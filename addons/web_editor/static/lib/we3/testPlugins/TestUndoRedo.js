(function () {
'use strict';

var TestUndoRedo = class extends we3.AbstractPlugin {
    static get autoInstall () {
        return ['Test'];
    }
    constructor () {
        super(...arguments);
        this.dependencies = ['Test', 'TestKeyboard'];

        // range collapsed: ◆
        // range start: ▶
        // range end: ◀


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
        // const doAnything = () => {
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
        // }

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
    }

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
    addition (options) {
        const keys = [
            'a',
            'ENTER',
            // ['CTRL', 'ENTER'],
            // ['CTRL', 'SHIFT', 'ENTER'],
            // ['CTRL', 'v'],
        ];
        const tests = [];
        keys.forEach((key)=>{
            options.iterations.forEach((iterIndex)=>{
                //addition
                let steps = [];
                for (let i = 0; i < iterIndex; i++) {
                    steps.push({key: key});
                }
                for (let i = 0; i < iterIndex; i++) {
                    steps.push({key: 'BACKSPACE'});
                }
                const optionsStr = `n='${iterIndex}' key=${key}`
                tests.push({
                    name: `'${optionsStr} addition multiples ADD then multiples BACK`,
                    content: options.content,
                    steps: steps,
                    test: options.content,
                });

                steps = [];
                for (let i = 0; i < iterIndex; i++) {
                    steps.push({key: key});
                    steps.push({key: 'BACKSPACE'});
                }
                tests.push({
                    name: `${optionsStr} addition multiples ADD/BACK`,
                    content: options.content,
                    steps: steps,
                    test: options.content,
                });
            });
            // options.iterations.forEach((i)=>{
            //     // deletion
            // });
            // options.iterations.forEach((i)=>{
            //     // addition n
            //     // deletion n
            // });
        });
        return tests;
    }

    _generateTests () {
        return this.addition({
            iterations: [1, 2, 3, 10],
            content: '<p>content that◆ is kind of long enough</p>'
        });
    }

    start () {
        this.dependencies.Test.add(this);
        return super.start();
    }

    test (assert) {
        return this.dependencies.TestKeyboard.test(assert, this._generateTests());
    }
};

we3.addPlugin('TestUndoRedo', TestUndoRedo);

})();
