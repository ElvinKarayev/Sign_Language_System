package com.ada.adminpanelsdp.repository;

import com.ada.adminpanelsdp.dto.VideoDTO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;


@Repository
public class VideoRepository {

    @Autowired
    private JdbcTemplate jdbcTemplate;
public List<VideoDTO> getAllVideos() {
    String sql = "SELECT * FROM public.videos ORDER BY video_id ASC LIMIT 100";

    return jdbcTemplate.query(sql, (rs, rowNum) -> {
        VideoDTO video = new VideoDTO();
        video.setVideoId(rs.getInt("video_id"));
        video.setTextId(rs.getInt("text_id"));
        video.setVideoReferenceId((Integer) rs.getObject("video_reference_id"));
        video.setUserId(rs.getInt("user_id"));
        video.setPositiveScores(rs.getInt("positive_scores"));
        video.setNegativeScores(rs.getInt("negative_scores"));
        video.setLanguage(rs.getString("language"));
        video.setFilePath(rs.getString("file_path"));
        video.setUploadedAt(rs.getTimestamp("uploaded_at"));
        video.setPoints(rs.getInt("points"));
        video.setClassroomId((UUID) rs.getObject("classroom_id"));
        return video;
    });
}

}
