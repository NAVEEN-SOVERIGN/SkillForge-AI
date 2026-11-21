import React from 'react';

export const BrandMark: React.FC<{ size?: number }> = ({ size = 26 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" role="img" aria-label="SkillForge connected evidence mark">
    <defs>
      <linearGradient id="skillforge-mark-line" x1="5" y1="5" x2="27" y2="28" gradientUnits="userSpaceOnUse"><stop stopColor="#DDF18E" /><stop offset="1" stopColor="#69D1B4" /></linearGradient>
    </defs>
    <path d="M8 8.5L16 16M24 8.5L16 16M16 16L8 24" stroke="url(#skillforge-mark-line)" strokeWidth="2.2" strokeLinecap="round" />
    <path d="M16 16L24 24" stroke="#E98768" strokeWidth="2.2" strokeLinecap="round" />
    <circle cx="8" cy="8" r="4.1" fill="#DDF18E" stroke="#164B4C" strokeWidth="1.5" />
    <circle cx="24" cy="8" r="4.1" fill="#69D1B4" stroke="#164B4C" strokeWidth="1.5" />
    <circle cx="16" cy="16" r="4.7" fill="#F7F9E6" stroke="#164B4C" strokeWidth="1.7" />
    <circle cx="8" cy="24" r="4.1" fill="#69D1B4" stroke="#164B4C" strokeWidth="1.5" />
    <circle cx="24" cy="24" r="4.1" fill="#E98768" stroke="#164B4C" strokeWidth="1.5" />
  </svg>
);

export default BrandMark;
