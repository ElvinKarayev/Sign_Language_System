// package com.ada.adminpanelsdp.controller;

// import com.ada.adminpanelsdp.dto.VideoDTO;
// import com.ada.adminpanelsdp.service.VideoService;
// import lombok.RequiredArgsConstructor;
// import org.springframework.http.ResponseEntity;
// import org.springframework.web.bind.annotation.*;

// import java.util.List;

// @RestController
// @RequestMapping("/api/videos")
// @CrossOrigin(origins = "*")
// @RequiredArgsConstructor
// public class VideoController {

//     private final VideoService videoService;

//     @GetMapping
//     public ResponseEntity<List<VideoDTO>> getAllVideos(@RequestParam(value = "keyword", required = false) String keyword) {
//         List<VideoDTO> videos = videoService.searchVideos(keyword);
//         if (videos.isEmpty()) return ResponseEntity.noContent().build();
//         return ResponseEntity.ok(videos);
//     }

//     @GetMapping("/{id}")
//     public ResponseEntity<VideoDTO> getVideoById(@PathVariable int id) {
//         return videoService.getAllVideos().stream()
//                 .filter(v -> v.getId() == id)
//                 .findFirst()
//                 .map(ResponseEntity::ok)
//                 .orElse(ResponseEntity.notFound().build());
//     }
// }
