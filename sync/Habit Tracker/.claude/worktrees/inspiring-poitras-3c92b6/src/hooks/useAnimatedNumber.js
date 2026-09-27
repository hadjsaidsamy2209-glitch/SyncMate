import { useState, useEffect } from 'react';

export function useAnimatedNumber(value) {
  const [display, setDisplay] = useState(value);

  useEffect(() => {
    const start = display;
    const steps = 20;
    const increment = (value - start) / steps;
    let current = 0;
    const interval = setInterval(() => {
      current++;
      setDisplay(Math.round(start + increment * current));
      if (current >= steps) clearInterval(interval);
    }, 16);
    return () => clearInterval(interval);
  }, [value]);

  return display;
}
