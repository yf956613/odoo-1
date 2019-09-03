odoo.define('rating.portal.composer', function (require) {
'use strict';

var portalChatter = require('portal.chatter');
var RatingSelector = require('portal.rating.composer').RatingSelector;

var PortalComposer = portalChatter.PortalComposer;

/**
 * PortalComposer
 *
 * Extends Portal Composer to handle rating submission
 */
PortalComposer.include({
    /**
     * @override
     */
    start: function () {
        var prom = [];
        prom.push(this._super.apply(this, arguments));
        if (this.options.display_rating) {
            var ratingSelector = new RatingSelector(this, this.options);
            prom.push(ratingSelector.insertAfter(this.$('.o_portal_chatter_composer_form input[name="csrf_token"]')));
        }
        return Promise.all(prom);
    },
});
});
