(function () {
'use strict';

var TestKeyboardArrow = class extends we3.AbstractPlugin {
    static get autoInstall () {
        return ['TestKeyboard'];
    }
    constructor () {
        super(...arguments);
        this.dependencies = ['Test', 'TestKeyboard'];

        // range collapsed: ◆
        // range start: ▶
        // range end: ◀

        // all <addition> possible:
        //======================
        // letter
        // enter
        // ctrl-enter
        // ctrl-shift-enter
        // paste
        // <selection>/copy/paste
        // widget
        // virtual text
        const addition = (options) => {
            const keys = [
                'a',
                'ENTER',
                ['CTRL', 'ENTER'],
                ['CTRL', 'SHIFT', 'ENTER'],
                // ['CTRL', 'v'],
            ];
            keys.forEach((key)=>{
                options.iterations.forEach((i)=>{
                    //addition
                });
                options.iterations.forEach((i)=>{
                    // deletion
                });
                options.iterations.forEach((i)=>{
                    // addition n
                    // deletion n
                });
            });
        };
        const deletion = (options) => {
            const keys = [
                'BACKSPACE'
            ];
        }
        const testAll = () => {
            addition({
                iterations: []
            });
        }
        const doAnything = () => {
            // cross product of:


            // all <deletion> possible:
            //======================
            // backspace
            // ctrl+backspace
            // <select>+backspace
            // <select>+cut

            // all <addition>/<deletion>:
            //======================
            // <selection>/copy/cut/paste

            // all <undo> possible:
            //======================
            // <deletion>
            // ctrl+z

            // all <redo> possible:
            //======================
            // ctrl+y

            // all <selection> possible:
            //======================
            // mouse
            //  click
            //  2x click
            //  3x click
            //  mousedown+mousemove+mouseup
            // keyboard
            //  shift+<movement_key>
            // [<selection_device>]

            // all <selection_device>
            //======================
            // mouse
            // keyboard
            // virtualkeyboard

            // all <movemement_key>
            //======================
            // left:right
            // right:left
            // up:down
            // down:up
            // pageup:pagedown
            // pagedown:pageup
            // home:end
            // end:home

            // $cross1=
            // edit n (letter,enter,tab,shifttab,ctrl,alt)/(backspace,ctrlz)
            // edit n (backspace,ctrlz)/(letter,enter,tab,shifttab,ctrl,alt)
            // move n left/right
            // move n top/down

            // $cross2=
            // select n character/$cross1
        }

        const editThenBackspace = (o) => {
            for (let i=0; i < 10;i++) {
                o.step({key: 'LEFT'});
                o.step({key: 'RIGHT'});
                doAnything();
            }
            for (let i=0; i < 10;i++) {
                o.step({key: 'LEFT'});
            }
            for (let i=0; i < 10;i++) {
                o.step({key: 'RIGHT'});
            }
        };

        this.keyboardTests = [
            // move one time left right
            // move x times left right
            // move x times left right + delete

            // test that for any move, the cursor is at the exacte same place
            // so doing
            // move
            // many editing
            // ctrl z

            {
                name: "LEFT move through virtual node",
                content: "<p>do\uFEFF◆m</p>",
                steps: [{
                    key: 'LEFT',
                }, {
                    key: 'LEFT',
                }, {
                    key: 'RIGHT',
                }, {
                    key: 'RIGHT',
                }],
                test: "<p>do\uFEFF◆m</p>",
            },
            {
                name: "LEFT move through virtual node",
                content: "<p>do\uFEFF◆m</p>",
                steps: [{
                    key: 'LEFT',
                }, {
                    key: 'LEFT',
                }, {
                    key: 'RIGHT',
                }, {
                    key: 'RIGHT',
                }],
                test: "<p>do\uFEFF◆m</p>",
            },
            {
                name: "LEFT collapse selection",
                content: "<p>dom▶ to◀ edit</p>",
                steps: [{
                    key: 'LEFT',
                }],
                test: "<p>dom◆ to edit</p>",
            },
            {
                name: "RIGHT collapse selection",
                content: "<p>dom▶ to◀ edit</p>",
                steps: [{
                    key: 'RIGHT',
                }],
                test: "<p>dom to◆ edit</p>",
            },
            {
                name: "RIGHT at end",
                content: "<p>dom to edit◆</p>",
                steps: [{
                    key: 'RIGHT',
                }],
                test: "<p>dom to edit◆</p>",
            },
            {
                name: "LEFT with on virtual text node",
                content: "<p>dom t\uFEFF◆o edit</p>",
                steps: [{
                    key: 'LEFT',
                }],
                test: "<p>dom ◆to edit</p>",
            },
            {
                name: "2 x LEFT with on virtual text node",
                content: "<p>dom t\uFEFFo◆ edit</p>",
                steps: [{
                    key: 'LEFT',
                }, {
                    key: 'LEFT',
                }],
                test: "<p>dom ◆to edit</p>",
            },
            {
                name: "2 x LEFT with 3 virtual text node",
                content: "<p>dom t\uFEFF\uFEFF\uFEFFo◆ edit</p>",
                steps: [{
                    key: 'LEFT',
                }, {
                    key: 'LEFT',
                }],
                test: "<p>dom ◆to edit</p>",
            },
            {
                name: "RIGHT with on virtual text node",
                content: "<p>dom t◆\uFEFFo edit</p>",
                steps: [{
                    key: 'RIGHT',
                }],
                test: "<p>dom to◆ edit</p>",
            },
            {
                name: "2 x RIGHT with on virtual text node",
                content: "<p>dom ◆t\uFEFFo edit</p>",
                steps: [{
                    key: 'RIGHT',
                }, {
                    key: 'RIGHT',
                }],
                test: "<p>dom to◆ edit</p>",
            },
            {
                name: "2 x RIGHT with 3 virtual text node",
                content: "<p>dom ◆t\uFEFF\uFEFF\uFEFFo edit</p>",
                steps: [{
                    key: 'RIGHT',
                }, {
                    key: 'RIGHT',
                }],
                test: "<p>dom to◆ edit</p>",
            },
            {
                name: "LEFT move before voidoid",
                content: '<p>dom to ▶<img src="/web_editor/static/src/img/transparent.png"/>◀ edit</p>',
                steps: [{
                    key: 'LEFT',
                }],
                test: '<p>dom to ◆<img src="/web_editor/static/src/img/transparent.png"/> edit</p>',
            },
            {
                name: "RIGHT move after voidoid",
                content: '<p>dom to ▶<img src="/web_editor/static/src/img/transparent.png"/>◀ edit</p>',
                steps: [{
                    key: 'RIGHT',
                }],
                test: '<p>dom to <img src="/web_editor/static/src/img/transparent.png"/>◆ edit</p>',
            },
            {
                name: "LEFT before image in image in table",
                content: '<table><tbody><tr><td><p>xxx</p></td><td><p>▶<img src="/web_editor/static/src/img/transparent.png"/>◀</p></td><td><p>yyy</p></td></tr></tbody></table>',
                steps: [{
                    key: 'LEFT',
                }],
                test: '<table><tbody><tr><td><p>xxx</p></td><td><p>◆<img src="/web_editor/static/src/img/transparent.png"/></p></td><td><p>yyy</p></td></tr></tbody></table>',
            },
            {
                name: "LEFT before image in table without spaces",
                content: '<table><tbody><tr><td><p>xxx</p></td><td><p>▶<img src="/web_editor/static/src/img/transparent.png"/>◀</p></td><td><p>yyy</p></td></tr></tbody></table>',
                steps: [{
                    key: 'LEFT',
                }],
                test: '<table><tbody><tr><td><p>xxx</p></td><td><p>◆<img src="/web_editor/static/src/img/transparent.png"/></p></td><td><p>yyy</p></td></tr></tbody></table>',
            },
            {
                name: "LEFT before image in table without spaces (2)",
                content: '<table><tbody><tr><td><p>xxx</p></td><td><p>▶<img src="/web_editor/static/src/img/transparent.png"/>◀</p></td><td><p>yyy</p></td></tr></tbody></table>',
                steps: [{
                    key: 'LEFT',
                }],
                test: '<table><tbody><tr><td><p>xxx</p></td><td><p>◆<img src="/web_editor/static/src/img/transparent.png"/></p></td><td><p>yyy</p></td></tr></tbody></table>',
            },
        ];
    }

    start () {
        this.dependencies.Test.add(this);
        return super.start();
    }

    test (assert) {
        return this.dependencies.TestKeyboard.test(assert, this.keyboardTests);
    }
};

we3.addPlugin('TestKeyboardArrow', TestKeyboardArrow);

})();
