odoo.define('payment_ogone.payment_form', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Widget = require('web.Widget');
    var PaymentForm = require('payment.payment_form');
       
    var qweb = core.qweb;
    var _t = core._t;
   
    PaymentForm.include({
    
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
    
        /**
         * called when clicking on pay now or add payment event to create token for credit card/debit card.
         *
         * @private
         * @param {Event} ev
         * @param {DOMElement} checkedRadio
         * @param {Boolean} addPmEvent
         */
        _OgoneTransaction: function (ev, $checkedRadio, addPmEvent) {
            var self = this;
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            var ds = $('input[name="data_set"]', acquirerForm)[0];
            var kwargs =  {"partner_id": this.options.partnerId};
            if (this.options.partnerId === undefined) {
                console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
                kwargs= {};
            }
            var formData = this.getFormData(inputsForm);
            var $ProcessingForm = $('#payment_method')
            var processData = this.getFormData($('input', $ProcessingForm));
            delete processData['cc_brand'];
            delete processData['cc_cvc'];
            delete processData['cc_expiry'];
            delete processData['cc_holder_name'];
            delete processData['csrf_token'];
            delete processData['cc_number'];

//            debugger;
//            problem= need to serialize the form...
//            var ProcessingForm = this.getFormData($.find('.o_payment_form'))

            var param_plus = {};
            param_plus['acquirerId'] = acquirerID ;
            param_plus['browserColorDepth'] = screen.colorDepth;
            param_plus['browserJavaEnabled'] =  navigator.javaEnabled() ;
            param_plus['browserLanguage'] = navigator.language;
            param_plus['browserScreenHeight'] = screen.height;
            param_plus['browserScreenWidth'] = screen.width;
            param_plus['browserTimeZone'] =  new Date().getTimezoneOffset();
            param_plus['browserUserAgent'] = navigator.userAgent;
            param_plus['FLAG3D'] = 'Y',
            param_plus['WIN3DS'] = 'POPUP',
            param_plus['return_url'] = formData['return_url'];
            param_plus['form_values'] = processData;
            param_plus[' '] = this.el["action"];
            kwargs['paramplus'] = param_plus;

            self._rpc({
                model: 'payment.token',
                method: 'ogone_prepare_token',
                context: self.context,
                kwargs: kwargs,
            }).then(function (result) {
                result['CVC'] = formData.cc_cvc;
                result['CARDNO'] = formData.cc_number.replace(/\s/g, '');
                result['ED'] = formData.cc_expiry.replace(/\s\/\s/g, '');
                result['CN'] = formData.cc_holder_name;
                // TEST if INPUT FORM IS VALID
                var APIUrl = "https://ogone.test.v-psp.com/ncol/test/Alias_gateway_utf8.asp";
                var ogoneForm = document.createElement("form");
                ogoneForm.method = "POST";
                ogoneForm.action = APIUrl;
                var el = document.createElement("input");
                el.setAttribute('type', 'submit');
                el.setAttribute('name', "Submit");
                ogoneForm.appendChild(el);
                _.each(result, function (value, key) {
                    var el = document.createElement("input");
                    el.setAttribute('type', 'hidden');
                    el.setAttribute('value', value);
                    el.setAttribute('name', key);
                    ogoneForm.appendChild(el);
                });
                document.body.appendChild(ogoneForm);;
                ogoneForm.submit();

            });
            
            // FLOW:
            // STEP 1
                // GET THE NEEDED INFORMATION FROM THE BACKEND;
                // ACCEPTURL
                // ALIASPERSISTEDAFTERUSE
                // EXCEPTIONURL
                // ORDERID
                // PSPID
                // SHASIGN : the token
                // PARAMPLUS if needed in the future
                // TODO talk about step 3 : transaction with additionnals parameters
            // STEP 2
                // Create the Token which is named Alias in Ogone denomination. This alias is created when submitting this form.(Pay Now)
                // The alias creation depends on the following fields:
                // ACCEPTURL
                // ALIASPERSISTEDAFTERUSE
                // CARDNO
                // CN
                // CVC
                // ED
                // EXCEPTIONURL
                // ORDERID
                // PSPID= SEE XML FILE
                // SHASIGN= xxx
        },
        
        /**
         * @override
         */
        updateNewPaymentDisplayStatus: function () {
            var $checkedRadio = this.$('input[type="radio"]:checked');
            var acquirerId = this.getAcquirerIdFromRadio($checkedRadio);
            if ($checkedRadio.length !== 1) {
                return;
            }
    
            //  hide add token form for ngenico
            if ($checkedRadio.data('provider') === 'ogone' && this.isNewPaymentRadio($checkedRadio)) {
                //this.$('[id*="o_payment_add_token_acq_"]');
                this.$('#o_payment_add_token_acq_' + acquirerId).removeClass('d-none');
            } else {
                this._super.apply(this, arguments);
            }
        },
    
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
    
        /**
         * @override
         */
        payEvent: function (ev) {
            ev.preventDefault();
            var $checkedRadio = this.$('input[type="radio"]:checked');
            // first we check that the user has selected a Ogone as s2s payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'ogone') {
                this._OgoneTransaction(ev, $checkedRadio);
            } else {
                this._super.apply(this, arguments);
            }
        },
        /**
         * @override
         */
        addPmEvent: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            var $checkedRadio = this.$('input[type="radio"]:checked');
    
            // first we check that the user has selected a Ogone as add payment method
            if ($checkedRadio.length === 1 && this.isNewPaymentRadio($checkedRadio) && $checkedRadio.data('provider') === 'ogone') {
                this._OgoneTransaction(ev, $checkedRadio, true);
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
    return PaymentForm;
    });
