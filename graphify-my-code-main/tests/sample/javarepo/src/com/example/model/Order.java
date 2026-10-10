package com.example.model;

public class Order {
    private final String id;
    private boolean paid;

    public Order(String id) { this.id = id; }
    public String getId() { return id; }
    public boolean isPaid() { return paid; }
    public void markPaid() { this.paid = true; }
}
