package com.example.service;

import com.example.model.Order;

public class PaymentService {
    public void charge(Order order) {
        System.out.println("charging " + order.getId());
    }
}
