package com.ada.adminpanelsdp.service;

import com.ada.adminpanelsdp.dto.UserDTO;
import com.ada.adminpanelsdp.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class UserService {

    @Autowired
    private UserRepository userRepository;

    public List<UserDTO> getAllUsers() {
        return userRepository.findAll();
    }
}
