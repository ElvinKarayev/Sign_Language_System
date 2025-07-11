package com.ada.adminpanelsdp.service;

import com.ada.adminpanelsdp.dto.UserDTO;
import com.ada.adminpanelsdp.repository.UserRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public List<UserDTO> getAllUsers() {
        return userRepository.findAll();
    }
}
