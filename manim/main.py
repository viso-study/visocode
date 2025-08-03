from manim_voiceover_fixed import VoiceoverScene
from manim_voiceover_fixed.services.gtts import GTTSService

from manim import *


class Manim(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", transcription_model="base"))

        # Title
        title = Text("Why is the Sky Blue?", font_size=48).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        with self.voiceover(
            text="Have you ever wondered why the sky appears blue on a clear day?"
        ):
            self.play(title.animate.shift(0.5 * UP))

        # Sunlight representation
        sun = Circle(radius=0.5, color=YELLOW, fill_opacity=1).to_corner(UL)
        self.play(Create(sun))
        self.wait(0.5)

        with self.voiceover(
            text="It all comes down to how sunlight interacts with the Earth's atmosphere."
        ):
            pass

        # Atmosphere representation
        atmosphere_rect = (
            Rectangle(width=7, height=3, color=BLUE_D, fill_opacity=0.2)
            .move_to(ORIGIN)
            .scale(0.8)
        )
        atmosphere_text = Text("Atmosphere", font_size=24).next_to(
            atmosphere_rect, DOWN
        )
        self.play(Create(atmosphere_rect), Write(atmosphere_text))
        self.wait(0.5)

        # Sunlight beam entering atmosphere
        sun_beam_start = Line(start=LEFT * 4, end=LEFT * 2, color=WHITE)
        sun_beam_end = Line(
            start=LEFT * 2, end=atmosphere_rect.get_center() + LEFT * 1, color=WHITE
        )
        sun_beam = VGroup(sun_beam_start, sun_beam_end)

        with self.voiceover(
            text="Sunlight, which appears white to us, is actually made up of all the colors of the rainbow, each with a different wavelength. As sunlight enters the atmosphere, it encounters tiny gas molecules, like nitrogen and oxygen."
        ):
            self.play(Create(sun_beam))
            self.play(FadeOut(sun))  # Fade out sun to focus on atmosphere
            self.play(atmosphere_rect.animate.scale(1.1))

        # Spectrum of light
        spectrum_text = Text("Sunlight = All Colors", font_size=24).next_to(
            atmosphere_rect, UP, buff=1.0
        )
        self.play(Write(spectrum_text))
        self.wait(0.5)

        # Rayleigh Scattering explanation
        spectrum_colors = (
            VGroup(
                Text("Violet", color=PURPLE, font_size=20),
                Text("Indigo", color=BLUE_D, font_size=20),
                Text("Blue", color=BLUE, font_size=20),
                Text("Green", color=GREEN, font_size=20),
                Text("Yellow", color=YELLOW, font_size=20),
                Text("Orange", color=ORANGE, font_size=20),
                Text("Red", color=RED, font_size=20),
            )
            .arrange(RIGHT, buff=0.2)
            .next_to(spectrum_text, DOWN, buff=0.5)
        )

        blue_text = spectrum_colors[2]
        violet_text = spectrum_colors[0]

        with self.voiceover(
            text="These molecules scatter sunlight in all directions. This is called Rayleigh scattering. Shorter wavelengths, like blue and violet, are scattered much more effectively than longer wavelengths, like red and orange."
        ):
            self.play(FadeOut(spectrum_text))
            self.play(Write(spectrum_colors))
            self.play(
                Indicate(blue_text, color=BLUE), Indicate(violet_text, color=PURPLE)
            )
            self.play(FadeOut(sun_beam))  # Fade out the sun beam

        # Scattering visualization
        num_molecules = 25
        gas_molecules = VGroup()
        for _ in range(num_molecules):
            # Correctly get a random 2D position within the atmosphere rectangle
            x_pos = np.random.uniform(
                -atmosphere_rect.width / 2 * 0.9, atmosphere_rect.width / 2 * 0.9
            )
            y_pos = np.random.uniform(
                -atmosphere_rect.height / 2 * 0.9, atmosphere_rect.height / 2 * 0.9
            )
            pos = atmosphere_rect.get_center() + np.array([x_pos, y_pos, 0])
            dot = Dot(color=WHITE, radius=0.05).move_to(pos)
            gas_molecules.add(dot)

        self.play(Create(gas_molecules))

        # Scattering effect
        scattered_light_blue = VGroup()
        scattered_light_violet = VGroup()
        scattered_light_red = VGroup()

        # Simulate scattering - more blue and violet, less red
        for _ in range(20):
            # Generate random positions within the atmosphere rectangle
            x_pos = np.random.uniform(
                -atmosphere_rect.width / 2 * 0.9, atmosphere_rect.width / 2 * 0.9
            )
            y_pos = np.random.uniform(
                -atmosphere_rect.height / 2 * 0.9, atmosphere_rect.height / 2 * 0.9
            )
            pos = atmosphere_rect.get_center() + np.array(
                [x_pos, y_pos, 0]
            )  # Ensure pos is a 3D vector

            if len(scattered_light_blue) < 15:  # More blue
                dot_blue = Dot(color=BLUE, radius=0.03).move_to(pos)
                scattered_light_blue.add(dot_blue)
            if len(scattered_light_violet) < 10:  # Even more violet
                dot_violet = Dot(color=PURPLE, radius=0.03).move_to(pos)
                scattered_light_violet.add(dot_violet)
            if len(scattered_light_red) < 5:  # Less red
                dot_red = Dot(color=RED, radius=0.03).move_to(pos)
                scattered_light_red.add(dot_red)

        self.play(
            *[FadeOut(mol) for mol in gas_molecules],
            *[Create(dot) for dot in scattered_light_blue],
            *[Create(dot) for dot in scattered_light_violet],
            *[Create(dot) for dot in scattered_light_red],
        )

        # Our eyes' perception
        eye = Circle(radius=0.2, color=WHITE, fill_opacity=1).to_edge(RIGHT)
        eye_text = Text("Our Eyes", font_size=20).next_to(eye, UP)

        with self.voiceover(
            text="Because blue and violet light are scattered all over the sky, our eyes perceive the sky as blue. Violet light is scattered even more, but our eyes are more sensitive to blue, which is why we see a blue sky."
        ):
            self.play(
                FadeOut(atmosphere_rect),
                FadeOut(atmosphere_text),
                FadeOut(spectrum_colors),
                FadeOut(scattered_light_red),
                scattered_light_blue.animate.scale(2).set_opacity(0.5),
                scattered_light_violet.animate.scale(2).set_opacity(0.5),
            )
            self.play(Create(eye), Write(eye_text))

        # Final thought
        final_text = Text("That's why the sky is blue!", font_size=36).to_edge(DOWN)
        with self.voiceover(
            text="Sunsets are red because the longer wavelengths of light are less scattered and can travel directly to our eyes when the sun is low on the horizon."
        ):
            self.play(Write(final_text))
            self.play(
                FadeOut(eye),
                FadeOut(eye_text),
                FadeOut(scattered_light_blue),
                FadeOut(scattered_light_violet),
            )

        self.wait(1)
