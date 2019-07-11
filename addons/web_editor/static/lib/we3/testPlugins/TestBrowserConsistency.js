(function () {
'use strict';

var TestBrowserConsistency = class extends we3.AbstractPlugin {
    static get autoInstall () {
        return ['Test'];
    }
    constructor () {
        super(...arguments);
        this.dependencies = ['Test', 'TestKeyboard'];

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
            content: '<p>content th◆at is kind of long enough</p>'
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

we3.addPlugin('TestBrowserConsistency', TestBrowserConsistency);

})();
