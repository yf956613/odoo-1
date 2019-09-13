odoo.define("point_of_sale.Chrome", function(require) {
    "use strict";

    const { _t } = require("web.core");
    const UsernameWidget = require("point_of_sale.UsernameWidget");
    const ProductScreenWidget = require("point_of_sale.ProductScreenWidget");
    const OrderSelectorWidget = require("point_of_sale.OrderSelectorWidget");

    class Chrome extends owl.Component {
        constructor() {
            super(...arguments);

            this.state = {
                loading: true,
                loadingMessage: _t("Loading"),
                loadingProgress: 0.0,
            };
        }

        async mounted() {
            super.mounted();
            this.env.model.on("loading", this._updateLoading, this);
            this.env.model.on("loaded", this._resetLoading, this);
            await this.env.model.ready;
            this.env.model.trigger("loaded");
        }

        willUnmount() {
            this.env.model.off("loading", this._updateLoading, this);
            this.env.model.off("loaded", this._resetLoading, this);
            super.willUnmount();
        }

        _updateLoading(msg, progress) {
            this.state.loading = true;
            this.state.loadingMessage = msg;
            this.state.loadingProgress = progress;
        }

        _resetLoading() {
            this.state.loading = false;
            this.state.loadingMessage = _t("Loading");
            this.state.loadingProgress = 0.0;
        }
    }

    Chrome.components = {
        UsernameWidget,
        ProductScreenWidget,
        OrderSelectorWidget,
    };

    return Chrome;
});
