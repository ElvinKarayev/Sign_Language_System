package com.ada.adminpanelsdp.dto;

import java.sql.Timestamp;
import java.util.UUID;

public class VideoDTO {
    private int videoId;
    private int textId;
    private Integer videoReferenceId;
    private int userId;
    private int positiveScores;
    private int negativeScores;
    private String language;
    private String filePath;
    private Timestamp uploadedAt;
    private int points;
    private UUID classroomId;

    // Getters and setters
    public int getVideoId() { return videoId; }
    public void setVideoId(int videoId) { this.videoId = videoId; }

    public int getTextId() { return textId; }
    public void setTextId(int textId) { this.textId = textId; }

    public Integer getVideoReferenceId() { return videoReferenceId; }
    public void setVideoReferenceId(Integer videoReferenceId) { this.videoReferenceId = videoReferenceId; }

    public int getUserId() { return userId; }
    public void setUserId(int userId) { this.userId = userId; }

    public int getPositiveScores() { return positiveScores; }
    public void setPositiveScores(int positiveScores) { this.positiveScores = positiveScores; }

    public int getNegativeScores() { return negativeScores; }
    public void setNegativeScores(int negativeScores) { this.negativeScores = negativeScores; }

    public String getLanguage() { return language; }
    public void setLanguage(String language) { this.language = language; }

    public String getFilePath() { return filePath; }
    public void setFilePath(String filePath) { this.filePath = filePath; }

    public Timestamp getUploadedAt() { return uploadedAt; }
    public void setUploadedAt(Timestamp uploadedAt) { this.uploadedAt = uploadedAt; }

    public int getPoints() { return points; }
    public void setPoints(int points) { this.points = points; }

    public UUID getClassroomId() { return classroomId; }
    public void setClassroomId(UUID classroomId) { this.classroomId = classroomId; }
}
