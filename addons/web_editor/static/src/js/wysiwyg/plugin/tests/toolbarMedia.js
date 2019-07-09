(function () {
    'use strict';

    var TestToolbarMedia = class extends we3.AbstractPlugin {
        static get autoInstall() {
            return ['Test', 'TestToolbar', 'Text'];
        }

        constructor() {
            super(...arguments);
            this.dependencies = ['Test', 'TestToolbar'];

            // range collapsed: ◆
            // range start: ▶
            // range end: ◀

            var self = this;
            const _triggerEvents = async function (selector, events) {
                return await self.dependencies.Test.triggerNativeEvents(document.querySelector(selector), events);
            }
            var _clickMedia = async function () {
                return await _triggerEvents('we3-toolbar we3-button[name="image-dialog"]', ['mousedown', 'click'])
            };
            const _insertVideo = async function (videoUrl) {
                await _clickMedia();
                await _triggerEvents('we3-tablist we3-button[role="tab"][name="video"]', ['mousedown', 'click'])
                const formControl = document.querySelector('textarea.form-control');
                formControl.value = videoUrl;
                await self.dependencies.Test.triggerNativeEvents(formControl, ['keyup']);
                await _triggerEvents('we3-modal we3-footer we3-button.we3-primary', ['mousedown', 'click']);
            };
            const _insertPictogram = async function (className) {
                await _clickMedia();
                await _triggerEvents('we3-tablist we3-button[role="tab"][name="pictogram"]', ['mousedown', 'click'])
                await _triggerEvents('we3-group[class="we3-pictogram"] we3-document[data-id="fa-glass"]', ['mousedown', 'click']);
                await _triggerEvents('we3-modal we3-footer we3-button.we3-primary', ['mousedown', 'click']);
            };
            var _editInput = async function (selector, value) {
                var $input = $(selector).first();
                $input.val(value);
                return self.dependencies.Test.triggerNativeEvents($input[0], ['input']);
            };
            var _uploadAndInsertImg = async function (url) {
                await _editInput('we3-modal input[name="url"]', url);
                await _triggerEvents('we3-modal we3-button[data-method="_onURLButtonClick"]', ['mousedown', 'click']);
                await _triggerEvents('we3-modal we3-footer we3-button.we3-primary', ['mousedown', 'click']);
            };

            this.toolbarTests = [
            {
                name: 'Click ADD A VIDEO (youtube) in empty p: p -> div iframe before p',
                async: false,
                content: '<p>◆</p>',
                do: async function (assert, testName) {
                    await _insertVideo('https://www.youtube.com/watch?v=xxxxxxxxxxx');
                    // debugger
                },
                test: '▶<div class="media_iframe_video">'+
                        '<div class="media_iframe_video_size"></div>'+
                        '<iframe width="1280" height="720" frameborder="0" class="o_video_dialog_iframe" src="//www.youtube.com/embed/xxxxxxxxxxx?autoplay=0&amp;loop=0&amp;controls=1&amp;fs=1&amp;modestbranding=1"/>'+
                    '</div>◀'+
                    '<p></p>',
            },
            // todo: make the test work by spliting the "p" node (in the Rules or Arch?)
            // {
            //     name: "Add VIDEO (youtube) in p in breakable in unbreakable in breakable: p -> div.media_iframe_video after p",
            //     async: true,
            //     content: '<div><div class="unbreakable"><p>before◆after</p></div></div>',
            //     do: async function () {
            //         await _insertVideo('https://www.youtube.com/watch?v=xxxxxxxxxxx');
            //     },
            //     test: '<div><div class="unbreakable"><p>before</p>' +
            //             '▶<div class="media_iframe_video">'+
            //                 '<div class="media_iframe_video_size"></div>'+
            //                 '<iframe width="1280" height="720" frameborder="0" class="o_video_dialog_iframe" src="//www.youtube.com/embed/xxxxxxxxxxx?autoplay=0&amp;loop=0&amp;controls=1&amp;fs=1&amp;modestbranding=1"/>'+
            //             '</div>◀'+
            //         '<p>after</p></div></div>',
            // },

            // Remove video
            {
                name: "Click REMOVE in popover after adding video in empty p",
                async: true,
                content: '<p>◆<br/></p>',
                do: async function () {
                    await _insertVideo('https://www.youtube.com/watch?v=xxxxxxxxxxx');
                    await _triggerEvents('we3-popover[name="Video"] we3-button[name="image-remove"]', ['mousedown', 'click']);
                },
                test: '<p><br/>◆</p>',
            },
            // /* VIDEO POPOVER */
            // Multiple clicks
            // todo: make the test work by spliting the "p" node (in the Rules or Arch?)
            // {
            //     name: "Click FLOAT CENTER then FLOAT LEFT in popover after adding youtube video in empty p",
            //     async: true,
            //     content: '<p>◆<br/></p>',
            //     do: async function () {
            //         await _insertVideo('https://www.youtube.com/watch?v=xxxxxxxxxxx');
            //         await _triggerEvents('we3-popover[name="Video"] we3-button[name="align-center"]', ['mousedown', 'click']);
            //         await _triggerEvents('we3-popover[name="Video"] we3-button[name="align-left"]', ['mousedown', 'click']);
            //     },
            //     test: '<p><br/></p>'+
            //             '<div class="media_iframe_video pull-left">'+
            //                 '<div class="media_iframe_video_size"></div>'+
            //                 '<iframe width="1280" height="720" frameborder="0" class="o_video_dialog_iframe" src="//www.youtube.com/embed/xxxxxxxxxxx?autoplay=0&amp;loop=0&amp;controls=1&amp;fs=1&amp;modestbranding=1"/>'+
            //             '</div>'+
            //         '<p><br/></p>',
            // },
            // Replace picture
            // todo: make the test work by spliting the "p" node (in the Rules or Arch?)
            // {
            //     name: "replace picture with video",
            //     async: true,
            //     content: '<p>▶<img src="https://www.odoo.com/logo.png"/>◀</p>',
            //     do: async function () {
            //         await _insertVideo('https://www.youtube.com/watch?v=xxxxxxxxxxx');
            //     },
            //     test: '<p><br/></p>'+
            //             '▶<div class="media_iframe_video">'+
            //                 '<div class="media_iframe_video_size"></div>'+
            //                 '<iframe width="1280" height="720" frameborder="0" class="o_video_dialog_iframe" src="//www.youtube.com/embed/xxxxxxxxxxx?autoplay=0&amp;loop=0&amp;controls=1&amp;fs=1&amp;modestbranding=1"/>'+
            //             '</div>◀'+
            //         '<p><br/></p>',
            // },
            // Replace video
            // todo: to uncomment after testing the pictogram
            // {
            //     name: "replace video by pictogram",
            //     async: true,
            //     content: '<p><br/></p>'+
            //             '▶<div class="media_iframe_video">'+
            //                 '<div class="media_iframe_video_size"></div>'+
            //                 '<iframe width="1280" height="720" frameborder="0" class="o_video_dialog_iframe" src="//www.youtube.com/embed/xxxxxxxxxxx?autoplay=0&amp;loop=0&amp;controls=1&amp;fs=1&amp;modestbranding=1"/>'+
            //             '</div>◀'+
            //             '<p><br/></p>',
            //     do: async function () {
            //         await _insertPictogram('fa-star');
            //     },
            //     test: '<p><br/></p>'+
            //             '<p>▶<i title="fa-star" aria-label="fa-star" role="img" class="fa fa-star"></i>◀</p>' +
            //         '<p><br/></p>',
            // },
            // {
            //     name: "replace video by pictogram (2)",
            //     async: true,
            //     content: '<p>aaa</p>'+
            //         '▶<div class="media_iframe_video">'+
            //             '<div class="media_iframe_video_size"></div>'+
            //             '<iframe width="1280" height="720" frameborder="0" class="o_video_dialog_iframe" src="//www.youtube.com/embed/xxxxxxxxxxx?autoplay=0&amp;loop=0&amp;controls=1&amp;fs=1&amp;modestbranding=1"/>'+
            //         '</div>◀'+
            //         '<p>bbb</p>',
            //     do: async function () {
            //         await _insertPictogram('fa-star');
            //     },
            //     test: '<p>aaa▶<i title="fa-star" aria-label="fa-star" role="img" class="fa fa-star"></i>◀</span>bbb</p>',
            // },


            {
                name: "Click ADD AN IMAGE URL in empty p: p -> img in p",
                async: true,
                content: '<p><br/>◆</p>',
                do: async function (assert, testName) {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                    assert.strictEqual($('we3-popover[name="Image"]').css('display'), 'flex', testName + ' (popover)');
                },
                test: '<p>▶<img title="https://www.odoo.com/logo.png" alt="https://www.odoo.com/logo.png" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image"/>◀</p>',
            },
            {
                name: "add an image in a table",
                async: true,
                content: '<section><div class="container"><div class="row"><div class="col-lg-6">' +
                    '<table class="table table-bordered">' +
                    '    <tbody>' +
                    '        <tr>' +
                    '            <td>' +
                    '                aaa' +
                    '            </td>' +
                    '            <td>' +
                    '                bb◆b' +
                    '            </td>' +
                    '            <td>' +
                    '                ccc' +
                    '            </td>' +
                    '        </tr>' +
                    '    </tbody>' +
                    '</table>' +
                    '</div></div></div></section>',
                do: async function () {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: '<section><div class="container"><div class="row"><div class="col-lg-6">' +
                        '<table class="table table-bordered">' +
                            '<tbody>' +
                                '<tr>' +
                                    '<td>' +
                                        'aaa' +
                                    '</td>' +
                                    '<td>' +
                                        'bb<img title="https://www.odoo.com/logo.png" alt="https://www.odoo.com/logo.png" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image"/>◆b' +
                                    '</td>' +
                                    '<td>' +
                                        'ccc' +
                                    '</td>' +
                                '</tr>' +
                            '</tbody>' +
                        '</table>' +
                        '</div></div></div></section>',
            },
            // BR IS NOT REMOVED AND IS ALWAYS PUT FIRST ?
            // {
            //     name: "add an image in an empty table",
            //     async: true,
            //     content: '<section><div class="container"><div class="row"><div class="col-lg-6">' +
            //         '<table class="table table-bordered">' +
            //         '    <tbody>' +
            //         '        <tr>' +
            //         '            <td>' +
            //         '                <br/>' +
            //         '            </td>' +
            //         '            <td>' +
            //         '                ◆<br/>' +
            //         '            </td>' +
            //         '            <td>' +
            //         '                <br/>' +
            //         '            </td>' +
            //         '        </tr>' +
            //         '    </tbody>' +
            //         '</table>' +
            //         '</div></div></div></section>',
            //     do: async function () {
            //         await _clickMedia();
            //         await _uploadAndInsertImg('https://www.odoo.com/logo.png');
            //     },
            //     test: '<section><div class="container"><div class="row"><div class="col-lg-6">' +
            //             '<table class="table table-bordered">' +
            //                 '<tbody>' +
            //                     '<tr>' +
            //                         '<td>' +
            //                             '<br/>' +
            //                         '</td>' +
            //                         '<td>' +
            //                             '▶<img title="https://www.odoo.com/logo.png" alt="https://www.odoo.com/logo.png" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image"/>◀<br/>' +
            //                         '</td>' +
            //                         '<td>' +
            //                             '<br/>' +
            //                         '</td>' +
            //                     '</tr>' +
            //                 '</tbody>' +
            //             '</table>' +
            //             '</div></div></div></section>',
            // },
            /* IMAGE POPOVER */
            {
                name: "Click PADDING XL in popover after adding image in empty p",
                async: true,
                content: '<p>◆</p>',
                do: async function () {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-toggler[title="Padding"]')[0], ['mousedown', 'click']);
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-button[name="padding-xl"]')[0], ['mousedown', 'click']);
                },
                test: '<p>▶<img title="https://www.odoo.com/logo.png" alt="https://www.odoo.com/logo.png" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image padding-xl"/>◀</p>',
            },
            {
                name: "Click IMAGE SIZE 25% in popover after adding image in empty p",
                async: true,
                content: '<p>◆</p>',
                do: async function () {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-button[name="size-25"]')[0], ['mousedown', 'click']);
                },
                test: '<p>▶<img title="https://www.odoo.com/logo.png" alt="https://www.odoo.com/logo.png" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image" style="width:25%"/>◀</p>',
            },
            {
                name: "Click FLOAT RIGHT in popover after adding image in empty p",
                async: true,
                content: '<p>◆</p>',
                do: async function () {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-button[name="align-right"]')[0], ['mousedown', 'click']);
                },
                test: '<p>▶<img title="https://www.odoo.com/logo.png" alt="https://www.odoo.com/logo.png" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image pull-right"/>◀</p>',
            },
            {
                name: "Click FLOAT CENTER then FLOAT LEFT in popover after adding image in empty p",
                async: true,
                content: '<p>◆</p>',
                do: async function () {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-button[name="align-center"]')[0], ['mousedown', 'click']);
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-button[name="align-left"]')[0], ['mousedown', 'click']);
                },
                test: '<p>▶<img title="https://www.odoo.com/logo.png" alt="https://www.odoo.com/logo.png" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image pull-left"/>◀</p>',
            },
            {
                name: "Click SHAPE ROUNDED in popover after adding image in empty p",
                async: true,
                content: '<p>◆</p>',
                do: async function () {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-button[name="rounded-circle"]')[0], ['mousedown', 'click']);
                },
                test: '<p>▶<img title="https://www.odoo.com/logo.png" alt="https://www.odoo.com/logo.png" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image rounded-circle"/>◀</p>',
            },
            // Remove picture
            {
                name: "Click REMOVE in popover after adding image in empty p",
                async: true,
                content: '<p>◆</p>',
                do: async function () {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-button[name="image-remove"]')[0], ['mousedown', 'click']);
                },
                test: '<p>◆</p>',
            },
            {
                name: "Click DESCRIPTION in popover after adding image in empty p",
                async: true,
                content: '<p>◆</p>',
                do: async function () {
                    await _clickMedia();
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                    await self.dependencies.Test.triggerNativeEvents($('we3-popover[name="Image"] we3-button[data-method="alt"]')[0], ['mousedown', 'click']);
                    $('we3-modal input#alt').val('Description');
                    $('we3-modal input#title').val('Title');
                    await self.dependencies.Test.triggerNativeEvents($('we3-modal we3-footer we3-button.we3-primary')[0], ['mousedown', 'click']);
                },
                test: '<p>▶<img title="Title" alt="Description" src="https://www.odoo.com/logo.png" class="img-fluid o_image o_we_custom_image"/>◀</p>',
            },
            ];
        }

        start() {
            this.dependencies.Test.add(this);
            return super.start();
        }

        test(assert) {
            return this.dependencies.TestToolbar.test(assert, this.toolbarTests);
        }
    };

    we3.addPlugin('TestToolbarMedia', TestToolbarMedia);

})();
