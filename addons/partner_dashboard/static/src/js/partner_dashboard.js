odoo.define('openerp_website.partner_dashboard', function (require) {
'use strict';

var sAnimation = require('website.content.snippets.animation');

sAnimation.registry.textarea_dashboard = sAnimation.Class.extend({
    selector: ".load_editor",

    start: function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        var $textarea = this.$target;
        if (!$textarea.val().match(/\S/)) {
            $textarea.val("<p><br/></p>");
        }
        var $form = $textarea.closest('form');
        var toolbar = [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['history', ['undo', 'redo']],
                ['insert', ['link', 'picture']]
        ];

        $textarea.summernote({
                height: 150,
                toolbar: toolbar,
                styleWithSpan: false
        });

        return def;
    },
    destroy: function () {
        this._super.apply(this, arguments);
        this.$target.summernote('destroy');
    },
});

sAnimation.registry.chart_dashboard = sAnimation.Class.extend({
    selector: "#chart",
    start: function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }
        var self = this;
        nv.addGraph(function() {
            var chart = nv.models.discreteBarChart()
                .x(function(d) { return d.label; })    //Specify the data accessors.
                .y(function(d) { return d.value; })
                .staggerLabels(true)    //Too many bars and not enough room? Try staggering labels.
                .showValues(true)       //...instead, show the bar value right on top of each bar.
                .color(["#87597b"])
                ;
            chart.yAxis.tickFormat(d3.format(',f'));
            chart.valueFormat(d3.format('d'));

            var values_dic = self.$el.data('size');

            d3.select(self.$el.find('svg')[0])
              .datum(function(){
                  return [
                    {
                      key: "Lead by Company Size",
                      values: values_dic
                    }
                  ];
                }
              )
              .call(chart);

            nv.utils.windowResize(chart.update);

            return chart;
        });
        return def;
    },
    destroy: function () {
        this._super.apply(this, arguments);
        d3.select(self.el).selectAll('svg').remove();
    },
});
sAnimation.registry.img_dashboard = sAnimation.Class.extend({
    selector: ".readUrl",
    read_events: {
        'change': '_onChange',
    },
    _onChange: function () {
        if (this.el.files && this.el.files[0]) {
            var reader = new FileReader();
            var self = this;
            reader.onload = function (e) {
                self.$el.closest('form').find('.img_preview').attr('src', e.target.result);
            };

            reader.readAsDataURL(this.el.files[0]);
        }
    },
});
});
