package com.example.jms;

import org.springframework.jms.annotation.JmsListener;
import org.springframework.stereotype.Component;

@Component
public class OrderEvents {
    @JmsListener(destination = "order.events")
    public void onOrderEvent(String payload) {
        System.out.println(payload);
    }
}
