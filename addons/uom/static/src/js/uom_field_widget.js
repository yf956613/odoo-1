odoo.define('uom.UomFieldWidget', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var basic_fields = require('web.basic_fields');
var fieldUtils = require('web.field_utils');
var field_registry = require('web.field_registry');
var utils = require('web.utils');


var _t = core._t;

var FieldFloat = basic_fields.FieldFloat;
var DebouncedField = basic_fields.DebouncedField

var FieldUom = FieldFloat.extend({
    supportedFieldTypes: ['float', 'uom'],
    resetOnAnyFieldChange: true, // Have to listen to uom changes

    events: _.extend({}, DebouncedField.prototype.events, {
        'input': '_onInput',
    }),

    /**
     * Float fields using a uom widget have an additional uom_field
     * parameter which defines the name of the field from which the uom
     * should be read.
     *
     * If no uom field is given or the field does not exist, we fallback
     * to the default input behavior instead.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._setUom();
        this.formatOptions.uom = this.uom;
    },

    /**
     * Re-gets the uom as its value may have changed.
     * @see FieldUom.resetOnAnyFieldChange
     *
     * @override
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        this._setUom();
    },

    /**
     * Deduces the uom description from the field options and view state.
     * The description is then available at this.uom.
     *
     * @private
     */
    _setUom: function () {
        var uomField = this.nodeOptions.uom_field || this.field.uom_field || 'uom_id';
        var uomID = this.record.data[uomField] && this.record.data[uomField].res_id;
        this.uom = session.uoms[uomID];
        this.formatOptions.uom = this.uom; // _formatValue() uses formatOptions
    },

    /**
     * Allow to enter decimal digits base on the uom's rounding value.
     *
     * @override
     * @private
     */
    _onInput: function() {
        this._super.apply(this, arguments);
        var value = this.$input.val();
        var uom_precision = this.formatOptions.uom && this.formatOptions.uom.decimal_places;
        if (value.includes('.')) {
            var precision = value.split('.')[1].length;
            if (uom_precision < precision) {
                this.do_warn(_.str.sprintf(_t('Only %s decimal digits are allow.'), uom_precision));
                this.$input.val(value.slice(0,-1))
            }
        }
    },

});

field_registry
    .add('uom', FieldUom);

/**
 * Returns a string representing a float.  The result takes into account the
 * user settings (to display the correct decimal separator).
 *
 * @param {float|false} value the value that should be formatted
 * @param {Object} [field] a description of the field (returned by fields_get
 *   for example).  It may contain a description of the number of digits that
 *   should be used.
 * @param {Object} [options] additional options to override the values in the
 *   python description of the field.
 * @param {Object} [options.uom] the description of the uom to use
 * @param {integer} [options.uom_id]
 *        the id of the 'uom.uom' to use (ignored if options.uom)
 * @param {string} [options.uom_field]
 *        the name of the field whose value is the uom id
 *        (ignore if options.uom or options.uom_id)
 *        Note: if not given it will default to the field uom_field value
 *        or to 'uom_id'.
 * @param {Object} [options.data]
 *        a mapping of field name to field value, required with
 *        options.uom_field
 * @returns {string}
 */
fieldUtils.format.uom = function(value, field, options) {
    options = options || {};
    if (value === false) {
        return "";
    }
    var uom = options && options.uom;
    if (!uom) {
        var uom_id = options.uom_id;
        if (!uom_id && options.data) {
            var uom_field = options.uom_field || field.uom_field || 'uom_id';
            uom_id = options.data[uom_field] && options.data[uom_field].res_id;
        } else if (!uom_id && options) {
            var uom_field = options.uom_field || field.uom_field || 'uom_id';
            uom_id = options[uom_field] && options[uom_field].res_id;
        }
        uom = session.uoms[uom_id];
    }

    var l10n = core._t.database.parameters;
    var precision;
    if (uom && uom.decimal_places) {
        precision = uom.decimal_places;
    } else {
        precision = 0;
    }
    var formatted = _.str.sprintf('%.' + precision + 'f', value || 0).split('.');
    formatted[0] = utils.insert_thousand_seps(formatted[0]);
    return formatted.join(l10n.decimal_point);
};

fieldUtils.parse.uom = function(value) {
    return fieldUtils.parse.float(value);
};

});
