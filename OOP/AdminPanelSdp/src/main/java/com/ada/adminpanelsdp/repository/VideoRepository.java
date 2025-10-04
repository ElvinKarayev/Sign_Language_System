package com.ada.adminpanelsdp.repository;

import java.time.Duration;
import java.util.List;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import com.ada.adminpanelsdp.dto.VideoDTO;

import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PresignedGetObjectRequest;

@Repository
public class VideoRepository {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    // Fetch all videos
    public List<VideoDTO> getAllVideos() {
        String sql = """
            SELECT 
                v.video_id,
                v.video_reference_id,
                v.user_id,
                v.positive_scores,
                v.negative_scores,
                v.language,
                v.file_path,
                v.uploaded_at,
                v.points,
                v.classroom_id,
                u.username,
                s.sentence_content AS full_sentence
            FROM public.videos v
            JOIN public.users u ON v.user_id = u.user_id
            JOIN public.sentences s ON v.text_id = s.sentence_id
            ORDER BY v.video_id ASC
            LIMIT 100
        """;

        return jdbcTemplate.query(sql, (rs, rowNum) -> mapRowToVideoDTO(rs));
    }

    // Search videos by keyword
    public List<VideoDTO> searchByKeyword(String keyword) {
        String sql = """
            SELECT 
                v.video_id,
                v.video_reference_id,
                v.user_id,
                v.positive_scores,
                v.negative_scores,
                v.language,
                v.file_path,
                v.uploaded_at,
                v.points,
                v.classroom_id,
                u.username,
                s.sentence_content AS full_sentence
            FROM public.videos v
            JOIN public.users u ON v.user_id = u.user_id
            JOIN public.sentences s ON v.text_id = s.sentence_id
            WHERE 
                CAST(v.video_id AS TEXT) LIKE ? OR
                CAST(v.user_id AS TEXT) LIKE ? OR
                LOWER(u.username) LIKE ? OR
                LOWER(s.sentence_content) LIKE ? OR
                CAST(v.video_reference_id AS TEXT) LIKE ? OR
                LOWER(v.language) LIKE ?
            ORDER BY v.video_id ASC
            LIMIT 100
        """;

        String likePattern = "%" + keyword.toLowerCase() + "%";

        return jdbcTemplate.query(
            sql,
            new Object[]{likePattern, likePattern, likePattern, likePattern, likePattern, likePattern},
            (rs, rowNum) -> mapRowToVideoDTO(rs)
        );
    }

    // Map SQL row to VideoDTO
    private VideoDTO mapRowToVideoDTO(java.sql.ResultSet rs) throws java.sql.SQLException {
        VideoDTO video = new VideoDTO();
        video.setVideoId(rs.getInt("video_id"));
        video.setVideoReferenceId((Integer) rs.getObject("video_reference_id"));
        video.setUserId(rs.getInt("user_id"));
        video.setPositiveScores(rs.getInt("positive_scores"));
        video.setNegativeScores(rs.getInt("negative_scores"));
        video.setLanguage(rs.getString("language"));
        video.setFilePath(rs.getString("file_path"));
        video.setUploadedAt(rs.getTimestamp("uploaded_at"));
        video.setPoints(rs.getInt("points"));
        video.setClassroomId((UUID) rs.getObject("classroom_id"));
        video.setUsername(rs.getString("username"));
        video.setFullSentence(rs.getString("full_sentence"));

        // Generate presigned URL
        video.setPresignedUrl(generatePresignedUrl(video.getFilePath()));
        return video;
    }

    // Generate AWS S3 presigned URL
    private String generatePresignedUrl(String filePath) {
        if (filePath == null || !filePath.contains("vesilebucket")) return null;

        try {
            String s3Key = filePath.replace("https://vesilebucket.s3.amazonaws.com/", "");

            S3Presigner presigner = S3Presigner.builder()
                    .region(Region.EU_CENTRAL_1)
                    .build();

            GetObjectRequest getObjectRequest = GetObjectRequest.builder()
                    .bucket("vesilebucket")
                    .key(s3Key)
                    .build();

            GetObjectPresignRequest presignRequest = GetObjectPresignRequest.builder()
                    .signatureDuration(Duration.ofMinutes(60))
                    .getObjectRequest(getObjectRequest)
                    .build();

            PresignedGetObjectRequest presignedRequest = presigner.presignGetObject(presignRequest);
            presigner.close();
            return presignedRequest.url().toString();

        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }
}
