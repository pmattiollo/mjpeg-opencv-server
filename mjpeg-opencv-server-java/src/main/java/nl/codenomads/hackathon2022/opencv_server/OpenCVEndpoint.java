package nl.codenomads.hackathon2022.opencv_server;

import org.bytedeco.ffmpeg.global.avutil;
import org.bytedeco.javacpp.Loader;
import org.bytedeco.javacv.FFmpegFrameGrabber;
import org.bytedeco.javacv.OpenCVFrameConverter;
import org.bytedeco.opencv.opencv_java;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.resteasy.annotations.cache.Cache;
import org.opencv.core.*;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;
import org.opencv.objdetect.CascadeClassifier;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Response;
import javax.ws.rs.core.StreamingOutput;

import static java.lang.Thread.MAX_PRIORITY;


@Path("/processed.jpg")
public class OpenCVEndpoint {
    static {
        Loader.load(opencv_java.class);
        avutil.av_log_set_level(MAX_PRIORITY);
    }
    private final OpenCVFrameConverter.ToMat converterToMat = new OpenCVFrameConverter.ToMat();

    private final CascadeClassifier face_cascade = new CascadeClassifier(getClass().getResource("/opencv/haarcascade_frontalface_default.xml").getPath());

    private final FFmpegFrameGrabber capture;

    public OpenCVEndpoint(@ConfigProperty(name = "mjpg-streamer.url") final String mjpgStreamerUrl) throws Exception {
        capture = new FFmpegFrameGrabber(mjpgStreamerUrl);
        capture.start();
    }

    private static final String NL = "\r\n";
    private static final String BOUNDARY = "--boundary";
    private static final String HEAD = NL + NL + BOUNDARY + NL +
            "Content-Type: image/jpeg" + NL +
            "Content-Length: ";

    @GET
    @Cache(noCache = true, isPrivate = true)
    @Produces("multipart/x-mixed-replace;boundary=" + BOUNDARY)
    public Response stream() {
        final StreamingOutput stream = os -> {
            while (true) {
                try {
                    final var frame = grabFrame();
                    final var image = Mat2JpegBytes(frame);
                    os.write((HEAD + image.length + NL + NL).getBytes());
                    os.write(image);
                    os.flush();
                    Thread.sleep(10);
                } catch (final InterruptedException e) {
                    throw new RuntimeException(e);
                }
            }
        };

        return Response.ok(stream).build();
    }

    private Mat grabFrame() {
        var frame = new Mat();
        try {
            frame = converterToMat.convertToOrgOpenCvCoreMat(this.capture.grabImage());

            // if the frame is not empty, process it
            if (!frame.empty()) {
                // your frame processing
                face_detect(frame);
            }

        } catch (final Exception e) {
            System.err.println("Exception during the image elaboration: " + e);
        }

        return frame;
    }

    static byte[] Mat2JpegBytes(final Mat matrix) {
        final MatOfByte mob = new MatOfByte();
        Imgcodecs.imencode(".jpg", matrix, mob);
        return mob.toArray();
    }


    // Example frame processing
    private void face_detect(final Mat matrix) {
        final var greyMatrix = new Mat();
        Imgproc.cvtColor(matrix, greyMatrix, Imgproc.COLOR_BGR2GRAY);
        final var faces = new MatOfRect();
        face_cascade.detectMultiScale(greyMatrix, faces, 1.3, 5);
        if (!faces.empty()) {
            for (final var face : faces.toArray()) {
                final var face_x = face.x + face.width / 2.0;
                final var face_y = face.y + face.height / 2.0;
                Imgproc.circle(matrix, new Point(face_x, face_y), (face.width + face.height) / 4, new Scalar(0, 255, 0), 2);
            }
        }
    }
}
