package nl.codenomads.hackathon2022.opencv_server;

import io.quarkus.qute.Template;
import io.quarkus.qute.TemplateInstance;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.MediaType;


@Path("/")
public class RootEndpoint {
    private final Template index;

    @ConfigProperty(name = "mjpg-streamer.url")
    String mjpgStreamerUrl;

    public RootEndpoint(final Template index) {
        this.index = index;
    }

    @GET
    @Produces(MediaType.TEXT_HTML)
    public TemplateInstance index() {
        return index.data("mjpg-streamer-url", mjpgStreamerUrl);
    }

}
