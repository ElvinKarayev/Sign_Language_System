package com.ada.adminpanelsdp.dto;

public class UserDTO {
    private Long id;
    private String username;
    private String country;
    private String role;
    private String telegramId;

    // Getters and setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getCountry() { return country; }
    public void setCountry(String country) { this.country = country; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getTelegramId() { return telegramId; }
    public void setTelegramId(String telegramId) { this.telegramId = telegramId; }
}
