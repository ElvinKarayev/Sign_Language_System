package com.ada.adminpanelsdp.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import javax.sql.DataSource;
import java.io.IOException;
import java.util.Properties;

@Configuration
public class DataSourceConfig {

    @Bean
    public DataSource dataSource() throws IOException {
        Properties props = ConfigLoader.loadDatabaseConfig();

        String url = "jdbc:postgresql://" + props.getProperty("db_host") + ":" + props.getProperty("db_port") + "/" + props.getProperty("db_name");

        DriverManagerDataSource dataSource = new DriverManagerDataSource();
        dataSource.setDriverClassName("org.postgresql.Driver");
        dataSource.setUrl(url);
        dataSource.setUsername(props.getProperty("db_user"));
        dataSource.setPassword(props.getProperty("db_password"));

        return dataSource;
    }

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }
}
