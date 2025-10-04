package com.ada.adminpanelsdp.service;

import com.ada.adminpanelsdp.dto.VideoDTO;
import com.ada.adminpanelsdp.repository.VideoRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class VideoService {

    @Autowired
    private VideoRepository videoRepository;

    // Fetch all videos with full sentence joined from sentences table
    public List<VideoDTO> getAllVideos() {
        return videoRepository.getAllVideos();
    }

    // Search videos using keyword (matches sentence, username, language, etc.)
    public List<VideoDTO> searchVideos(String keyword) {
        return videoRepository.searchByKeyword(keyword);
    }
}
