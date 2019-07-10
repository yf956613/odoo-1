odoo.define('web_editor.we3_tests', function (require) {
"use strict";

var ajax = require('web.ajax');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var Wysiwyg = require('web_editor.wysiwyg');


QUnit.module('web_editor', {
    beforeEach: function () {
        this.data = weTestUtils.wysiwygData({
            'note.note': {
                fields: {
                    display_name: {
                        string: "Displayed name",
                        type: "char"
                    },
                    body: {
                        string: "Message",
                        type: "html"
                    },
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    body: "<p>toto toto toto</p><p>tata</p>",
                }],
            },
        });

        testUtils.mock.patch(ajax, {
            loadAsset: function (xmlId) {
                if (xmlId === 'template.assets') {
                    return Promise.resolve({
                        cssLibs: [],
                        cssContents: ['body {background-color: red;}']
                    });
                }
                if (xmlId === 'template.assets_all_style') {
                    return Promise.resolve({
                        cssLibs: $('link[href]:not([type="image/x-icon"])').map(function () {
                            return $(this).attr('href');
                        }).get(),
                        cssContents: ['body {background-color: red;}']
                    });
                }
                throw 'Wrong template';
            },
        });

        var self = this;
        testUtils.mock.patch(Wysiwyg, {
            init: function () {
                this._super(...arguments);
                var testsList = this._editorOptions().tests;
                var testPlugins = weTestUtils.getTestPlugins(self.testOptions.plugins, testsList);
                this.options = Object.assign({}, this.options, {
                    plugins: Object.assign({}, this.options.plugins, testPlugins, {
                        Test: true,
                    }),
                    test: Object.assign({
                        callback: self.testOptions.resolve,
                        auto: true,
                        assert: self.testOptions.assert,
                    }, this.options.test),
                });
            }
        });
    },
    afterEach: function () {
        testUtils.mock.unpatch(Wysiwyg);
        testUtils.mock.unpatch(ajax);
    },
}, function () {

    QUnit.module('default rendering & options');

    async function createFormAndTest (self) {
        var promise = new Promise((resolve) => self.testOptions.resolve = resolve);

        var form = await testUtils.createView({
            View: FormView,
            model: 'note.note',
            data: self.data,
            arch: '<form><field name="body" widget="html" style="height: 100px"/></form>',
            mockRPC: function (route, args) {
                if (route.indexOf('data:image/png;base64') === 0) {
                    return Promise.resolve();
                }
                if (route.indexOf('youtube') !== -1) {
                    return Promise.resolve();
                }
                if (route.indexOf('/web_editor/static/src/img/') === 0) {
                    return Promise.resolve();
                }
                if (route === '/web_editor/attachment/add_url') {
                    return Promise.resolve({
                        id: 1,
                        public: true,
                        name: 'image',
                        mimetype: 'image/png',
                        checksum: false,
                        url: '/web_editor/static/src/img/transparent.png',
                        image_src: '/web_editor/static/src/img/transparent.png',
                        type: 'url',
                        res_id: 0,
                        res_model: false,
                        access_token: false,
                    });
                }
                return this._super(route, args);
            },
        });
        await promise;
        form.destroy();
        return promise;
    }

    var disableAllTests = { disableAllTests: true };

    QUnit.test('popover', async function (assert) {
        assert.expect(19);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestPopover: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('range', async function (assert) {
        assert.expect(8);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestRange: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('ui', async function (assert) {
        assert.expect(8);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestUI: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('renderer', async function (assert) {
        assert.expect(11);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestRenderer: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('complex default config (integration)', async function (assert) {
        assert.expect(6);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestComplex: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('change range with arrow', async function (assert) {
        assert.expect(19);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestKeyboardArrow: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('rules', async function (assert) {
        assert.expect(47);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestArchAndRules: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('toolbar color', async function (assert) {
        assert.expect(23);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, { TestToolbarColor: true }),
        };
        await createFormAndTest(this);
    });
    QUnit.test('toolbar indent', async function (assert) {
        assert.expect(9);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, { TestToolbarIndent: true }),
        };
        await createFormAndTest(this);
    });
    QUnit.test('toolbar keymap', async function (assert) {
        assert.expect(13);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, { TestToolbarKeymap: true }),
        };
        await createFormAndTest(this);
    });
    QUnit.test('toolbar link', async function (assert) {
        assert.expect(17);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, { TestToolbarLink: true }),
        };
        await createFormAndTest(this);
    });
    QUnit.test('toolbar list', async function (assert) {
        assert.expect(72);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, { TestToolbarList: true }),
        };
        await createFormAndTest(this);
    });
    QUnit.test('toolbar paragraph', async function (assert) {
        assert.expect(15);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, { TestToolbarParagraph: true }),
        };
        await createFormAndTest(this);
    });
    QUnit.test('toolbar wand', async function (assert) {
        assert.expect(18);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestToolbarWand: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('toolbar style', async function (assert) {
        assert.expect(28);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestToolbarFontStyle: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('unbreakable', async function (assert) {
        assert.expect(24);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestKeyboardUnbreakable: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('keyboard char', async function (assert) {
        assert.expect(36);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestKeyboardChar: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('keyboard tab', async function (assert) {
        assert.expect(15);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestKeyboardTab: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('keyboard enter', async function (assert) {
        assert.expect(64);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestKeyboardEnter: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('keyboard delete', async function (assert) {
        assert.expect(82);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestKeyboardDelete: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('keyboard complex dom', async function (assert) {
        assert.expect(21);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestKeyboardComplex: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('keyboard backspace', async function (assert) {
        assert.expect(101);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestKeyboardBackspace: true}),
        };
        await createFormAndTest(this);
    });
    QUnit.test('history', async function (assert) {
        assert.expect(35);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {TestHistory: true}),
        };
        await createFormAndTest(this);
    });

    QUnit.module('DropBlock plugins');

    var toolbarDropBlock = [
        'DropBlock',
        'FontStyle',
        'FontSize',
        'ForeColor', 'BgColor',
        'List',
        'Paragraph',
        'TablePicker',
        'LinkCreate',
        'Media',
        'History',
        'CodeView',
        'FullScreen',
        'KeyMap',
        'Test',
    ];

    QUnit.test('range + popover + rules + char + DropBlock', async function (assert) {
        assert.expect(98);

        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, {
                TestRange: true,
                TestPopover: true,
                TestArchAndRules: true,
                TestKeyboardChar: true,
            }),
            toolbar: toolbarDropBlock,
        };
        await createFormAndTest(this);
    });

    QUnit.test('DropBlock & DropBlockSelector', async function (assert) {
        assert.expect(36);

        this.testOptions = {
            assert: assert,
            plugins: Object.assign({
                DropBlockSelector: true,
            }, disableAllTests, {
                TestKeyboardChar: true,
            }),
            toolbar: toolbarDropBlock,
        };
        await createFormAndTest(this);
    });

    QUnit.test('DropBlock & CustomizeBlock', async function (assert) {
        assert.expect(51);

        this.testOptions = {
            assert: assert,
            plugins: Object.assign({
                CustomizeBlock: true,
            }, disableAllTests, {
                TestPopover: true,
                TestKeyboardChar: true,
            }),
            toolbar: toolbarDropBlock,
        };
        await createFormAndTest(this);
    });

    QUnit.module('Media');

    QUnit.test('Image', async function (assert) {
        assert.expect(15);
        this.testOptions = {
            assert: assert,
            plugins: Object.assign({}, disableAllTests, { TestToolbarMedia: true }),
        };
        await createFormAndTest(this);
    });

});

});
