package luminais.tech.appjava;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

import luminais.tech.appjava.model.DevopsProperties;

@SpringBootApplication
@EnableConfigurationProperties(DevopsProperties.class)
public class AppJavaApplication {

    public static void main(String[] args) {
        String debugEnv = System.getenv("DEBUG");
        if (debugEnv != null && debugEnv.equalsIgnoreCase("true")) {
            System.setProperty("logging.level.root", "DEBUG");
        }

        SpringApplication.run(AppJavaApplication.class, args);
    }

}
