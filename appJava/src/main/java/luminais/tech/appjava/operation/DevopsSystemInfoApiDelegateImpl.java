package luminais.tech.appjava.operation;

import jakarta.servlet.http.HttpServletRequest;

import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import luminais.tech.appjava.api.DevopsSystemInfoApiDelegate;
import luminais.tech.appjava.model.HealthResponse;
import luminais.tech.appjava.model.RootResponse;
import luminais.tech.appjava.service.DevopsInfoService;

/**
 * Operation layer: OpenAPI delegate that forwards to the service.
 */
@Service
public class DevopsSystemInfoApiDelegateImpl implements DevopsSystemInfoApiDelegate {

    private final DevopsInfoService devopsInfoService;

    public DevopsSystemInfoApiDelegateImpl(DevopsInfoService devopsInfoService) {
        this.devopsInfoService = devopsInfoService;
    }

    @Override
    public ResponseEntity<RootResponse> getInfo() {
        HttpServletRequest request = currentRequest();
        RootResponse body = devopsInfoService.buildRootResponse(request);
        return ResponseEntity.ok(body);
    }

    @Override
    public ResponseEntity<HealthResponse> getHealth() {
        HealthResponse body = devopsInfoService.buildHealthResponse();
        return ResponseEntity.ok(body);
    }

    private HttpServletRequest currentRequest() {
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        return attrs != null ? attrs.getRequest() : null;
    }
}
