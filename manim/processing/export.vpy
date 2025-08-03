import vapoursynth as vs  # type: ignore

core = vs.core
core.std.LoadPlugin(path="C:/Users/ai/dev/backend/manim/processing/VSFilterMod.dll")
core.std.LoadPlugin(path="C:/Users/ai/dev/backend/manim/processing/BestSource.dll")

# file names should be changed as appropriate
video = core.bs.VideoSource(
    source="C:/Users/ai/dev/backend/media/videos/main/1080p60/Video.mp4"
)
subtitled_video = core.vsfm.TextSubMod(video, "C:/Users/ai/dev/backend/media/Video.ass")
subtitled_video.set_output()

# Paths should be changed as appropriate
# vspipe -c y4m .\manim\processing\export.vpy .\manim\processing\temp.raw
# ffmpeg -i .\manim\processing\temp.raw .\manim\processing\temp.mp4
# rm .\manim\processing\temp.raw
# ffmpeg -i .\manim\processing\temp.mp4 -i .\media\videos\main\1080p60\Video.wav -c:v copy -c:a copy .\manim\processing\output_no_music.mp4
# rm .\manim\processing\temp.mp4
# ffmpeg -i .\manim\processing\output_no_music.mp4 -i '.\manim\processing\music\Moonlight Magic - Asher Fulero.mp3' -filter_complex "[1:a]volume=0.1[music];[0:a][music]amix=inputs=2:duration=first[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -shortest .\manim\processing\output.mp4
# rm .\manim\processing\output_no_music.mp4
# export and send back output.mp4
# clean up:
# rm .\media -r -force
# rm .\manim\processing\output.mp4
