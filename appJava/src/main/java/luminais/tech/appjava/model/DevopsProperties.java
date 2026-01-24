package luminais.tech.appjava.model;

import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Configuration properties for the DevOps info service.
 * <p>
 * Values are loaded from the {@code devops.*} section in application.yml.
 */
@ConfigurationProperties(prefix = "devops")
public record DevopsProperties(
        Service service,
        List<Endpoint> endpoints
) {

    public record Service(
            String name,
            String version,
            String description,
            String framework
    ) {}

    public record Endpoint(
            String path,
            String method,
            String description
    ) {}
}
