"""A Go to page tile with its icon alone (catalogue/screen.yaml `navigation`, display `icon`): how the add-on keeps it,
sends it and carries it through a page document, and that the firmware says it draws it."""
from copy import deepcopy
import itertools
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'screen_manager/app'))
import catalogue  # noqa: E402
from core import (ICON_ONLY_FEATURE, NAVIGATION_DISPLAYS, Grid, layout_snapshot, min_firmware, state_message,  # noqa: E402
                  validate_layout)
from layout_migrations import migrate_legacy  # noqa: E402
from page_layout import LayoutError, compile_tiles, validate_document  # noqa: E402
import tile_icons  # noqa: E402


def tile(entity, slot=None, name='', **options):
    item = {'entity': entity, 'name': name}
    if slot is not None:
        item['slot'] = slot
    if options:
        item['options'] = options
    return item


def options_of(*tiles, grid=None):
    return [item.get('options', {}) for item in validate_layout({'title': 'Home', 'tiles': list(tiles)}, grid=grid or Grid())['tiles']]


class Catalogue(unittest.TestCase):
    def test_the_faces_and_the_word_come_from_the_catalogue(self):
        self.assertEqual(NAVIGATION_DISPLAYS, ('standard', 'icon'))
        self.assertEqual(catalogue.option('screen', 'navigation', 'icon')['screen'], {'feature': 'icon_only', 'else': 'standard'})
        self.assertEqual(ICON_ONLY_FEATURE, 'icon_only')
        # The clock keeps its own faces: icon is a Go to page tile's alone.
        self.assertNotIn('icon', catalogue.display_keys('screen'))

    def test_the_firmware_says_it_and_draws_it(self):
        self.assertIn(f'features.add("{ICON_ONLY_FEATURE}");', (ROOT / 'packages/core.yaml').read_text())
        model = (ROOT / 'components/smart_display/runtime_model.h').read_text()
        self.assertIn(f'bool icon_only() const {{ return display == "{NAVIGATION_DISPLAYS[1]}" && is_page(); }}', model)


class Options(unittest.TestCase):
    def test_a_tile_without_a_face_keeps_its_standard_one(self):
        self.assertEqual(options_of(tile('screen.page_2', 0)), [{}])
        self.assertEqual(options_of(tile('screen.page_2', 0, icon='sofa', background='blue')), [{'icon': 'sofa', 'background': 'blue'}])

    def test_icon_only_is_kept_and_the_standard_face_is_never_stored(self):
        self.assertEqual(options_of(tile('screen.page_2', 0, display='icon')), [{'display': 'icon'}])
        self.assertEqual(options_of(tile('screen.page_2', 0, display='standard')), [{}])

    def test_any_other_face_still_goes_as_it_always_did(self):
        for face in ('digital', 'dial', 'watch', 'forecast', 'map', 'live', 'Icon', ''):
            with self.subTest(face=face):
                self.assertEqual(options_of(tile('screen.page_2', 0, display=face)), [{}])

    def test_switching_faces_keeps_everything_else(self):
        chosen = {'icon': 'sofa', 'background': 'green', 'sub': 'text:Living room', 'tap': 'auto'}
        alone = options_of(tile('screen.page_3', 0, 'Living', display='icon', **chosen))[0]
        self.assertEqual(alone, {**chosen, 'display': 'icon'})
        back = options_of(tile('screen.page_3', 0, 'Living', **{k: v for k, v in alone.items() if k != 'display'}))[0]
        self.assertEqual(back, chosen)

    def test_every_size_a_navigation_tile_takes(self):
        # 1x1, 2x1 (wide), 1x2 (tall), 2x2 (square) and the larger spans a 3 x 3 grid offers: the face changes nothing of it.
        grid = Grid(3, 3)
        for size in ('single', 'wide', 'tall', 'square', '3x1', '1x3', '3x2', '2x3'):
            with self.subTest(size=size):
                plain = options_of(tile('screen.page_2', 0, size=size), grid=grid)[0]
                self.assertEqual(options_of(tile('screen.page_2', 0, display='icon', size=size), grid=grid), [{**plain, 'display': 'icon'}])
        # The whole page stays a navigation tile's no: a face changes nothing there.
        with self.assertRaisesRegex(ValueError, 'single or double width'):
            options_of(tile('screen.page_2', 0, display='icon', size='full'))

    def test_icon_only_asks_no_newer_firmware(self):
        plain = validate_layout({'title': 'Home', 'tiles': [tile('screen.page_2', 0)]})
        alone = validate_layout({'title': 'Home', 'tiles': [tile('screen.page_2', 0, display='icon')]})
        self.assertEqual(min_firmware(alone), min_firmware(plain))


class Wire(unittest.TestCase):
    def test_the_screen_gets_the_face_with_the_icon_and_the_page(self):
        layout = validate_layout({'title': 'Home', 'tiles': [tile('screen.page_3', 0, 'Heating', display='icon', icon='radiator')]})
        message = state_message(0, layout['tiles'][0], {})
        self.assertEqual(message['entity'], 'screen.page_3')
        self.assertEqual(message['name'], 'Heating')
        self.assertEqual(message['o'], {'display': 'icon', 'icon': tile_icons.ICONS['radiator'][0]})
        # Its own arrow travels as nothing, as on the standard face: the screen draws it in the large face.
        self.assertEqual(state_message(0, tile('screen.page_3', 0, display='icon'), {})['o'], {'display': 'icon'})
        self.assertIn(tile_icons.BUILTIN_TILES['screen.page_1'], tile_icons.BIG_GLYPHS)

    def test_the_layout_sensor_says_the_face(self):
        layout = validate_layout({'title': 'Home', 'tiles': [tile('screen.page_3', 0, display='icon'), tile('screen.page_2', 1)]})
        snapshot = layout_snapshot({'name': 'Hall', 'node': 'hall'}, layout)
        self.assertEqual([(t['display'], t['to_page']) for t in snapshot['tiles']], [('icon', 3), ('standard', 2)])


class Documents(unittest.TestCase):
    def migrate(self, value, grid=None):
        counter = itertools.count(1)
        return migrate_legacy(value, grid or Grid(), lambda: f'{next(counter):016x}')

    def test_a_document_keeps_the_face_through_migration_and_compiling(self):
        old = {'title': 'Screen', 'pages': 3, 'tiles': [tile('screen.page_3', 0, 'Heating', display='icon', icon='radiator'),
                                                        tile('screen.page_2', 1, 'Blinds')]}
        record = self.migrate(old)
        first = record['layout']['pages'][0]['tiles']
        self.assertEqual(first[0]['appearance'].get('display'), 'icon')
        self.assertNotIn('display', first[1]['appearance'])
        validate_document(record['layout'], Grid())
        compiled = compile_tiles(record['layout'], Grid())
        self.assertEqual([(t['entity'], t.get('options', {}).get('display')) for t in compiled], [('screen.page_3', 'icon'), ('screen.page_2', None)])

    def test_a_document_refuses_a_face_it_would_change(self):
        layout = self.migrate({'title': 'Screen', 'pages': 2, 'tiles': [tile('screen.page_2', 0, display='icon')]})['layout']
        for face in ('standard', 'watch', 'digital'):
            with self.subTest(face=face):
                changed = deepcopy(layout)
                changed['pages'][0]['tiles'][0]['appearance']['display'] = face
                with self.assertRaises(LayoutError):
                    validate_document(changed, Grid())

    def test_every_reorder_keeps_the_target_and_the_face(self):
        record = self.migrate({'title': 'Screen', 'pages': 3, 'tiles': [tile('screen.page_3', 0, display='icon')]})
        original = record['layout']
        target = original['pages'][2]['id']
        for order in itertools.permutations(range(3)):
            with self.subTest(order=order):
                layout = deepcopy(original)
                layout['pages'] = [layout['pages'][i] for i in order]
                validate_document(layout, Grid())
                compiled = compile_tiles(layout, Grid())[0]
                self.assertEqual(compiled['entity'], f'screen.page_{order.index(2) + 1}')
                self.assertEqual(compiled['options'], {'display': 'icon'})
                source = next(page for page in layout['pages'] if page['tiles'])['tiles'][0]
                self.assertEqual(source['content']['target']['pageId'], target)


if __name__ == '__main__':
    unittest.main()
