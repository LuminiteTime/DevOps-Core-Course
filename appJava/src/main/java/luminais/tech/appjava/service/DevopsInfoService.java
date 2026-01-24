package luminais.tech.appjava.service;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;

import jakarta.servlet.http.HttpServletRequest;

import org.springframework.stereotype.Service;

import luminais.tech.appjava.model.DevopsProperties;
import luminais.tech.appjava.model.EndpointInfo;
import luminais.tech.appjava.model.HealthResponse;
import luminais.tech.appjava.model.RequestInfo;
import luminais.tech.appjava.model.RootResponse;
import luminais.tech.appjava.model.RuntimeInfo;
import luminais.tech.appjava.model.ServiceInfo;
import luminais.tech.appjava.model.SystemInfo;

/**
 * Service layer for building DevOps info responses.
 */
@Service
public class DevopsInfoService {

    private static final Instant START_TIME = Instant.now();

    private final DevopsProperties properties;

    public DevopsInfoService(DevopsProperties properties) {
        this.properties = properties;
    }

    public RootResponse buildRootResponse(HttpServletRequest request) {
        return new RootResponse(
            buildServiceInfo(),
            buildSystemInfo(),
            buildRuntimeInfo(),
            buildRequestInfo(request),
            buildEndpoints()
        );
    }

    public HealthResponse buildHealthResponse() {
        long uptimeSeconds = getUptimeSeconds();

        return new HealthResponse(
            "healthy",
            OffsetDateTime.now(ZoneOffset.UTC),
            uptimeSeconds
        );
    }

    private ServiceInfo buildServiceInfo() {
        DevopsProperties.Service cfg = properties.service();
        return new ServiceInfo(
            cfg.name(),
            cfg.version(),
            cfg.description(),
            cfg.framework()
        );
    }

    private SystemInfo buildSystemInfo() {
        String hostname = "unknown";
        try {
            hostname = InetAddress.getLocalHost().getHostName();
        } catch (UnknownHostException ignored) {
            // use default hostname
        }

        return new SystemInfo(
            hostname,
            System.getProperty("os.name", "unknown"),
            System.getProperty("os.version", "unknown"),
            System.getProperty("os.arch", "unknown"),
            Runtime.getRuntime().availableProcessors(),
            System.getProperty("java.version", "unknown")
        );
    }

    private RuntimeInfo buildRuntimeInfo() {
        long uptimeSeconds = getUptimeSeconds();
        long hours = uptimeSeconds / 3600;
        long minutes = (uptimeSeconds % 3600) / 60;

        return new RuntimeInfo(
            uptimeSeconds,
            hours + " hours, " + minutes + " minutes",
            OffsetDateTime.now(ZoneOffset.UTC),
            "UTC"
        );
    }

    private RequestInfo buildRequestInfo(HttpServletRequest request) {
        if (request == null) {
            return new RequestInfo(
                "unknown",
                "unknown",
                "UNKNOWN",
                "/"
            );
        }

        String userAgent = request.getHeader("User-Agent");

        return new RequestInfo(
            request.getRemoteAddr(),
            userAgent != null ? userAgent : "unknown",
            request.getMethod(),
            request.getRequestURI()
        );
    }

    private List<EndpointInfo> buildEndpoints() {
        List<EndpointInfo> endpoints = new ArrayList<>();
        for (DevopsProperties.Endpoint cfg : properties.endpoints()) {
            endpoints.add(new EndpointInfo(
                cfg.path(),
                cfg.method(),
                cfg.description()
            ));
        }
        return endpoints;
    }

    private long getUptimeSeconds() {
        return Duration.between(START_TIME, Instant.now()).getSeconds();
    }
}
