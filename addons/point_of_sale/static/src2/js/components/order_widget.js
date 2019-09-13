odoo.define("point_of_sale.OrderWidget", function(require) {
    "use strict";

    const Orderline = require("point_of_sale.Orderline");
    const AbstractPosConnectedComponent = require("point_of_sale.BackboneStore");

    class OrderWidget extends AbstractPosConnectedComponent {}
    OrderWidget.components = {Orderline};
    OrderWidget.mapStoreToProps = function(model) {
        const selectedOrder = model.get_order();
        const orderlines = selectedOrder ? selectedOrder.get_orderlines() : [];
        const total = selectedOrder ? selectedOrder.get_total_with_tax() : 0;
        const taxes = selectedOrder ? total - selectedOrder.get_total_without_tax() : 0;
        return {
            orderlines,
            selectedOrder,
            total,
            taxes,
        };
    };
    OrderWidget.props = ["orderlines", "selectedOrder", "total", "taxes"];

    return OrderWidget;
});
