odoo.define('web.Bus', function (require) {
"use strict";

var Class = require('web.Class');
var mixins = require('web.mixins');

/**
 * Event Bus used to bind events scoped in the current instance
 *
 * @class Bus
 */
return Class.extend(mixins.EventDispatcherMixin, {
    init: function (parent) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);
    },
    trigger: function () {
        this.__edispatcherEvents.trigger.apply(this.__edispatcherEvents, arguments);
        return this;
    },
});

});
