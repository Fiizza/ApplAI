import { useEffect, useRef } from 'react';
import * as THREE from 'three';

// A drifting constellation of nodes (your applications) with pulsing
// connective signal lines — resolves into the wordmark, then hands off
// to the app. Mounted only for the splash duration, then unmounted.
export default function Splash3D({ ambient = false }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 100);
    camera.position.z = 9;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    // --- nodes --- (ambient mode: sparser + dimmer, for use behind a card rather than as the hero)
    const NODE_COUNT = ambient ? 10 : 42;
    const nodePositions = [];
    const nodeGeo = new THREE.SphereGeometry(0.045, 8, 8);
    const nodeMatGold = new THREE.MeshBasicMaterial({ color: 0xff4fd8, transparent: ambient, opacity: ambient ? 0.28 : 1 });
    const nodeMatBlue = new THREE.MeshBasicMaterial({ color: 0x8b6bff, transparent: ambient, opacity: ambient ? 0.28 : 1 });
    const nodesGroup = new THREE.Group();

    for (let i = 0; i < NODE_COUNT; i++) {
      const radius = 3 + Math.random() * 2.2;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos((Math.random() * 2) - 1);
      const pos = new THREE.Vector3(
        radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.sin(phi) * Math.sin(theta) * 0.6,
        radius * Math.cos(phi)
      );
      nodePositions.push(pos);
      const mesh = new THREE.Mesh(nodeGeo, i % 6 === 0 ? nodeMatGold : nodeMatBlue);
      mesh.position.copy(pos);
      nodesGroup.add(mesh);
    }
    scene.add(nodesGroup);

    // --- connective lines between nearby nodes ---
    const lineGeoPoints = [];
    for (let i = 0; i < nodePositions.length; i++) {
      for (let j = i + 1; j < nodePositions.length; j++) {
        if (nodePositions[i].distanceTo(nodePositions[j]) < 2.1) {
          lineGeoPoints.push(nodePositions[i], nodePositions[j]);
        }
      }
    }
    const lineGeo = new THREE.BufferGeometry().setFromPoints(lineGeoPoints);
    const lineMat = new THREE.LineBasicMaterial({ color: 0x5b3d8a, transparent: true, opacity: ambient ? 0.22 : 0.45 });
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lines);

    // --- central signal pulse ---
    const pulseGeo = new THREE.SphereGeometry(0.12, 16, 16);
    const pulseMat = new THREE.MeshBasicMaterial({ color: 0xff4fd8, transparent: true, opacity: ambient ? 0.35 : 0.9 });
    const pulse = new THREE.Mesh(pulseGeo, pulseMat);
    scene.add(pulse);
    if (ambient) pulse.visible = false;

    let frame;
    const clock = new THREE.Clock();

    const animate = () => {
      const t = clock.getElapsedTime();
      nodesGroup.rotation.y = t * 0.12;
      lines.rotation.y = t * 0.12;
      pulse.scale.setScalar(1 + Math.sin(t * 2.2) * 0.25);
      pulseMat.opacity = 0.6 + Math.sin(t * 2.2) * 0.3;
      camera.position.x = Math.sin(t * 0.08) * 0.6;
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    animate();

    const handleResize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      nodeGeo.dispose();
      nodeMatGold.dispose();
      nodeMatBlue.dispose();
      lineGeo.dispose();
      lineMat.dispose();
      pulseGeo.dispose();
      pulseMat.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, [ambient]);

  return <div ref={mountRef} className="splash-canvas" />;
}
