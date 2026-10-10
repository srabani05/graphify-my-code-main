package com.example.service;

import com.example.model.Order;
import com.example.util.Validator;

public class OrderService {
    private final PaymentService payments;

    public OrderService(PaymentService payments) {
        this.payments = payments;
    }

    public Order processOrder(Order order) {
        Validator.check(order);
        if (order.isPaid()) {
            return order;
        }
        payments.charge(order);
        order.markPaid();
        return order;
    }
}
