import { useEffect, useRef } from 'react';

const VIDEO_SRC = '/halite_animation.webm';
const POSTER_SRC = '/halite-logo.png';

export default function CrystalMount() {
  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.muted = true;
    const play = () => {
      video.play().catch(() => {});
    };

    if (video.readyState >= 2) {
      play();
    } else {
      video.addEventListener('loadeddata', play, { once: true });
    }

    return () => video.removeEventListener('loadeddata', play);
  }, []);

  return (
    <div
      id="crystal-mount"
      className="flex h-[480px] w-[480px] items-center justify-center"
    >
      <video
        ref={videoRef}
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        poster={POSTER_SRC}
        className="h-full w-full object-contain"
      >
        <source src={VIDEO_SRC} type="video/webm" />
      </video>
    </div>
  );
}
