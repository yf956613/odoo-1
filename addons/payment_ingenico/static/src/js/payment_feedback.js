odoo.define('payment_ingenico.payment_feedback', function (require) {

    "use strict";
    var ajax = require('web.ajax');
    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    var _t = core._t;
    var qweb = core.qweb;

    publicWidget.registry.ogoneFeedback = publicWidget.Widget.extend({
        selector: '.o_payment_feedback',
        start: function () {
            this.feedback();
        },

        feedback: function() {
            var pm_id = this.$el.data('token-id');
            console.log("OGONE feedback JS LOADED");
            var self = this;
            var feedback_arguments_str = document.location.search;
//           https://css-tricks.com/snippets/jquery/get-query-params-object/
            // FIXME BETTER DO IT in python.
            // FIXME We only need the acquirer id here.
            var GetParameters = function(str) {
	                return (str || document.location.search).replace(/(^\?)/,'').split("&").map(function(n){return n = n.split("="),this[n[0]] = n[1],this}.bind({}))[0];
            }
            var feedback_arguments = GetParameters();
            var id =  parseInt(feedback_arguments['acquirerId'],10)
            var kwargs = {'parameters': feedback_arguments_str};
            self._rpc({
                model: 'payment.acquirer',
                method: 'ogone_alias_feedback',
                args: [id],
                context: self.context,
                kwargs: kwargs,
            }).then(function (result) {
                console.log(result);
                if (result.hasOwnProperty("error")){
                    console.error('error SHA')
                }
                var ogoneForm = document.createElement("form");
                ogoneForm.method = "POST";
                ogoneForm.action = result['action_url'];
                var el = document.createElement("input");
                el.setAttribute('type', 'submit');
                el.setAttribute('name', "Submit");
                ogoneForm.appendChild(el);
                console.log(result);
                _.each(result['payload'], function (value, key) {
                    var el = document.createElement("input");
                    el.setAttribute('type', 'hidden');
                    el.setAttribute('value', value);
                    el.setAttribute('name', key);
                    ogoneForm.appendChild(el);
                });
                document.body.appendChild(ogoneForm);;
                ogoneForm.submit();
            });
        },
    });
});