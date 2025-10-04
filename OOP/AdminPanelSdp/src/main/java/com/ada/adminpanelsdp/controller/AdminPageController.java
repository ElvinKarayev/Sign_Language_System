package com.ada.adminpanelsdp.controller;

import com.ada.adminpanelsdp.dto.UserDTO;
import com.ada.adminpanelsdp.dto.VideoDTO;
import com.ada.adminpanelsdp.service.UserService;
import com.ada.adminpanelsdp.service.VideoService;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

@Controller

public class AdminPageController {

    @Autowired
    private UserService userService;

    @Autowired
    private VideoService videoService;

    // Handles GET request for the admin panel page
    @GetMapping("/admin")
    public String showAdminPage(@RequestParam(value = "keyword", required = false) String keyword, Model model) {
        List<UserDTO> users = userService.getAllUsers();
        List<VideoDTO> videos;

        if (keyword != null && !keyword.trim().isEmpty()) {
            videos = videoService.searchVideos(keyword);
        } else {
            videos = videoService.getAllVideos();
        }

        model.addAttribute("users", users);
        model.addAttribute("videos", videos);
        return "admin"; // Returns admin.html Thymeleaf page
    }
}
