package luminais.tech.appjava;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

@SpringBootTest
class DevopsEndpointsTest {

    @Autowired
    private WebApplicationContext context;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(context).build();
    }

    @Test
    void healthReturnsExpectedFields() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("healthy"))
                .andExpect(jsonPath("$.timestamp").isString())
                .andExpect(jsonPath("$.uptime_seconds").isNumber());
    }

    @Test
    void rootReturnsExpectedStructure() throws Exception {
        mockMvc.perform(get("/"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.service.name").value("devops-info-service"))
                .andExpect(jsonPath("$.service.version").isString())
                .andExpect(jsonPath("$.service.framework").value("Spring Boot"))
                .andExpect(jsonPath("$.system.hostname").isString())
                .andExpect(jsonPath("$.runtime.uptime_seconds").isNumber())
                .andExpect(jsonPath("$.request.method").value("GET"))
                .andExpect(jsonPath("$.request.path").value("/"))
                .andExpect(jsonPath("$.endpoints").isArray());
    }

    @Test
    void unknownPathReturns404() throws Exception {
        mockMvc.perform(get("/does-not-exist"))
                .andExpect(status().isNotFound());
    }
}
