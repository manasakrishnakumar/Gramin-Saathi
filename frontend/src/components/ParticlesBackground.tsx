import { memo, useCallback } from "react";
import Particles from "react-tsparticles";
import type { Engine, ISourceOptions } from "tsparticles-engine";
import { loadSlim } from "tsparticles-slim";

export type ParticlesBackgroundProps = {
  className?: string;
};

export const ParticlesBackground = memo(({ className }: ParticlesBackgroundProps) => {
  const particlesInit = useCallback(async (engine: Engine) => {
    await loadSlim(engine);
  }, []);

  const options: ISourceOptions = {
    fullScreen: false,
    background: {
      color: { value: "transparent" },
    },
    fpsLimit: 45,
    detectRetina: true,
    reduceMotion: {
      enable: true,
      factor: 6,
      value: true,
    },
    interactivity: {
      detectsOn: "window",
      events: {
        onHover: { enable: false, mode: [] },
        onClick: { enable: false, mode: [] },
        resize: true,
      },
    },
    particles: {
      number: {
        value: 80,
        density: { enable: true, area: 900 },
      },
      color: {
        value: ["#2D5016", "#4A90E2", "#FF9933"],
      },
      opacity: {
        value: { min: 0.35, max: 0.65 },
        animation: {
          enable: true,
          speed: 0.8,
          minimumValue: 0.35,
        },
      },
      size: {
        value: { min: 2, max: 6 },
        animation: {
          enable: true,
          speed: 4,
          minimumValue: 2,
        },
      },
      links: {
        enable: true,
        color: "#2D5016",
        distance: 100,
        opacity: 0.4,
        width: 1,
      },
      move: {
        enable: true,
        direction: "none",
        speed: 1.2,
        straight: false,
        outModes: {
          default: "out",
        },
      },
    },
  };

  return (
    <Particles
      className={className}
      id="saathi-particles"
      init={particlesInit}
      options={options}
    />
  );
});

ParticlesBackground.displayName = "ParticlesBackground";

