odoo.define("point_of_sale.ProductScreenWidget", function(require) {
    "use strict";

    const ProductListWidget = require("point_of_sale.ProductListWidget");
    const ProductCategoriesWidget = require("point_of_sale.ProductCategoriesWidget");
    const OrderWidget = require("point_of_sale.OrderWidget");
    const ActionpadWidget = require("point_of_sale.ActionpadWidget");
    const NumpadWidget = require("point_of_sale.NumpadWidget");
    const AbstractPosConnectedComponent = require("point_of_sale.BackboneStore");

    class ProductScreenWidget extends AbstractPosConnectedComponent {
        constructor() {
            super(...arguments);

            this.selectProduct = this.selectProduct.bind(this);
        }

        selectProduct(product) {
            // eslint-disable-next-line no-console
            console.debug(product);
            if (product.to_weight && this.storeProps.config.iface_electronic_scale) {
                // TODO: this.gui.show_screen('scale',{product: product});
                this.storeProps.selectedOrder.add_product(product);
            } else {
                this.storeProps.selectedOrder.add_product(product);
            }
        }
    }

    ProductScreenWidget.components = {
        ProductListWidget,
        ProductCategoriesWidget,
        OrderWidget,
        ActionpadWidget,
        NumpadWidget,
    };

    ProductScreenWidget.mapStoreToProps = function(model) {
        const {currency, dp, units_by_id, config} = model;
        const selectedOrder = model.get_order();
        let pricelist = model.default_pricelist;
        if (selectedOrder) {
            pricelist = selectedOrder.pricelist;
        }
        return {
            products: model.db.get_product_by_category(0),
            unitsByUOM: units_by_id,
            currency,
            decimalPrecisions: dp,
            pricelist,
            selectedOrder,
            config,
        };
    };
    ProductScreenWidget.props = ["selectedOrder", "products", "pricelist", "unitsByUOM"];


    return ProductScreenWidget;
});
