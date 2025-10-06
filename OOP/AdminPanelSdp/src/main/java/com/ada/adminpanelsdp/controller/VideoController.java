package com.ada.adminpanelsdp.controller;

import com.ada.adminpanelsdp.dto.VideoDTO;
import com.ada.adminpanelsdp.service.VideoService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/videos")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class VideoController {

    private final VideoService videoService;

    public VideoController() {
        this.videoService = null;
    }

    // Get all videos or search
    @GetMapping
    public ResponseEntity<List<VideoDTO>> getVideos(@RequestParam(value = "keyword", required = false) String keyword) {
        List<VideoDTO> videos = (keyword == null || keyword.isEmpty()) ?
                videoService.getAllVideos() : videoService.searchVideos(keyword);
        if (videos.isEmpty()) return ResponseEntity.noContent().build();
        return ResponseEntity.ok(videos);
    }

    // Get a single video by ID
    @GetMapping("/{id}")
    public ResponseEntity<VideoDTO> getVideoById(@PathVariable int id) {
        VideoDTO video = videoService.getVideoById(id);
        if (video == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(video);
    }
}
