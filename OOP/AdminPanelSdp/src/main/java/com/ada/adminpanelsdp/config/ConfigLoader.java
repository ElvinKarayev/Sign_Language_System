package com.ada.adminpanelsdp.config;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

public class ConfigLoader {
    public static Properties loadDatabaseConfig() throws IOException {
        Properties props = new Properties();
        try (FileInputStream fis = new FileInputStream("config.txt")) {
            props.load(fis);
        }
        return props;
    }
}
