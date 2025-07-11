package com.ada.adminpanelsdp.repository;

import com.ada.adminpanelsdp.dto.UserDTO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

@Repository
public class UserRepository {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    public List<UserDTO> findAll() {
        String sql = "SELECT id, username, country, role, telegram_id FROM app_user";
        return jdbcTemplate.query(sql, (rs, rowNum) -> mapRowToUser(rs));
    }

    private UserDTO mapRowToUser(ResultSet rs) throws SQLException {
        UserDTO user = new UserDTO();
        user.setId(rs.getLong("id"));
        user.setUsername(rs.getString("username"));
        user.setCountry(rs.getString("country"));
        user.setRole(rs.getString("role"));
        user.setTelegramId(rs.getString("telegram_id"));
        return user;
    }
}
