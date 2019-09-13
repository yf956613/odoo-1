odoo.define("point_of_sale.BackboneStore", function() {
    "use strict";

    /**
     * Abstract class use by the pos to allow the sync between backbone and owl framework
     * All connected component use by the pos need to use these class
     * @abstract
     */
    class AbstractPosConnectedComponent extends owl.store.ConnectedComponent {

        constructor() {
            super(...arguments);
            this.__customDeepRevNumber = 0;
            this.__customRevNumber = 0;
        }
        /**
         * Overide the getStore because we use store using by the currently use the store current pos instance
         * @override
         * @param env
         * @returns {{state: *}}
         */
        getStore(env) {
            var self = this;
            env.model.observer = {
                deepRevNumber: function () {
                    return self.__customDeepRevNumber;
                },
                revNumber: function () {
                    return self.__customRevNumber;
                }
            };
            class store extends owl.core.EventBus {
                state = env.model;
                observer = {
                    deepRevNumber: function () {
                        return self.__customDeepRevNumber;
                    },
                    revNumber: function () {
                        return self.__customRevNumber;
                    }
                }
            }
            return new store();
        }

        __callMounted() {
            const model = this.__owl__.store.state;
            model.on("change", this.__checkUpdate, this);
            const ordersCollection = model.get("orders");
            ordersCollection.models.forEach(order => {
                this._registerOrderCheckUpdate(order);
            });
            ordersCollection.on("add", this._registerOrderCheckUpdate, this);
            ordersCollection.on("remove", this._unregisterOrderCheckUpdate, this);
            super.__callMounted();
        }

        willUnmount() {
            const model = this.__owl__.store.state;
            model.off("change", this.__checkUpdate, this);
            const ordersCollection = model.get("orders");
            ordersCollection.models.forEach(order => {
                this._unregisterOrderCheckUpdate(order);
            });
            ordersCollection.off("add", this._registerOrderCheckUpdate, this);
            ordersCollection.off("remove", this._unregisterOrderCheckUpdate, this);
            super.willUnmount();
        }

        __checkUpdate() {
            // eslint-disable-next-line no-console
            console.debug("__checkUpdate", arguments);
            this.__customDeepRevNumber++;
            this.__customRevNumber++;
            super.__checkUpdate();

        }

        _registerOrderCheckUpdate(order) {
            // eslint-disable-next-line no-console
            console.debug("_registerOrderCheckUpdate", order);
            order.orderlines.on("change", this.__checkUpdate, this);
        }

        _unregisterOrderCheckUpdate(order) {
            // eslint-disable-next-line no-console
            console.debug("_unregisterOrderCheckUpdate", order);
            order.orderlines.off("change", this.__checkUpdate, this);
        }
    };

    return AbstractPosConnectedComponent;
});
