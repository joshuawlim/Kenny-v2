import React, { ReactNode, forwardRef } from 'react';
import { IconButton, Card, CardProps, IconButtonProps } from '@mui/material';
import { useSpring, animated, useSpringValue, useTransition } from '@react-spring/web';

// Custom hook for hover and press animations
export const useHoverPressSpring = (
  targetScale = 1.06,
  pressScale = 0.98,
  stiffness = 220,
  damping = 18
) => {
  const [springs, api] = useSpring(() => ({
    scale: 1,
    y: 0,
    rotateX: 0,
    config: { tension: stiffness, friction: damping },
  }));

  const bind = {
    onMouseEnter: () => {
      api.start({ scale: targetScale, y: -2, rotateX: 5 });
    },
    onMouseLeave: () => {
      api.start({ scale: 1, y: 0, rotateX: 0 });
    },
    onMouseDown: () => {
      api.start({ scale: pressScale, y: 0, rotateX: 0 });
    },
    onMouseUp: () => {
      api.start({ scale: targetScale, y: -2, rotateX: 5 });
    },
  };

  return [springs, bind] as const;
};

// Animated Icon Button
interface AnimatedIconButtonProps extends IconButtonProps {
  hoverScale?: number;
  pressScale?: number;
  children: ReactNode;
}

export const AnimatedIconButton: React.FC<AnimatedIconButtonProps> = ({
  hoverScale = 1.06,
  pressScale = 0.98,
  children,
  sx = {},
  ...props
}) => {
  const [springs, bind] = useHoverPressSpring(hoverScale, pressScale);

  return (
    <animated.div style={springs}>
      <IconButton
        {...bind}
        sx={{
          transition: 'box-shadow 0.2s ease-in-out',
          ...sx,
        }}
        {...props}
      >
        {children}
      </IconButton>
    </animated.div>
  );
};

// Animated Card
interface AnimatedCardProps extends CardProps {
  hoverElevation?: boolean;
  entranceDelay?: number;
  children: ReactNode;
}

export const AnimatedCard = forwardRef<HTMLDivElement, AnimatedCardProps>(
  ({ hoverElevation = true, entranceDelay = 0, children, sx = {}, ...props }, ref) => {
    const [springs, bind] = useHoverPressSpring(1.02, 0.99, 300, 20);

    // Entrance animation
    const entranceSpring = useSpring({
      from: { opacity: 0, y: 20, scale: 0.95 },
      to: { opacity: 1, y: 0, scale: 1 },
      delay: entranceDelay,
      config: { tension: 200, friction: 20 },
    });

    return (
      <animated.div style={{ ...entranceSpring, ...springs }}>
        <Card
          ref={ref}
          {...(hoverElevation ? bind : {})}
          sx={{
            transition: 'all 0.2s ease-in-out',
            cursor: hoverElevation ? 'pointer' : 'default',
            '&:hover': hoverElevation
              ? {
                  boxShadow: '0 12px 40px rgba(0, 0, 0, 0.15)',
                  transform: 'translateY(-4px)',
                }
              : {},
            ...sx,
          }}
          {...props}
        >
          {children}
        </Card>
      </animated.div>
    );
  }
);

AnimatedCard.displayName = 'AnimatedCard';

// Animated List Items with stagger
interface AnimatedListProps {
  children: ReactNode[];
  staggerDelay?: number;
  direction?: 'up' | 'down' | 'left' | 'right';
}

export const AnimatedList: React.FC<AnimatedListProps> = ({
  children,
  staggerDelay = 100,
  direction = 'up',
}) => {
  const transitions = useTransition(children, {
    from: { 
      opacity: 0, 
      transform: getTransformForDirection(direction, true),
    },
    enter: (_, index) => async (next) => {
      await new Promise(resolve => setTimeout(resolve, index * staggerDelay));
      await next({ 
        opacity: 1, 
        transform: getTransformForDirection(direction, false),
      });
    },
    config: { tension: 200, friction: 20 },
  });

  return (
    <>
      {transitions((style, item, _, index) => (
        <animated.div key={index} style={style}>
          {item}
        </animated.div>
      ))}
    </>
  );
};

function getTransformForDirection(direction: string, isFrom: boolean): string {
  const distance = isFrom ? 30 : 0;
  switch (direction) {
    case 'up':
      return `translateY(${isFrom ? distance : 0}px)`;
    case 'down':
      return `translateY(${isFrom ? -distance : 0}px)`;
    case 'left':
      return `translateX(${isFrom ? distance : 0}px)`;
    case 'right':
      return `translateX(${isFrom ? -distance : 0}px)`;
    default:
      return `translateY(${isFrom ? distance : 0}px)`;
  }
}

// Animated Grid Container
interface AnimatedGridProps {
  children: ReactNode[];
  columns?: number;
  gap?: number;
}

export const AnimatedGrid: React.FC<AnimatedGridProps> = ({
  children,
  columns = 3,
  gap = 16,
}) => {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(auto-fit, minmax(300px, 1fr))`,
        gap: `${gap}px`,
      }}
    >
      {children.map((child, index) => (
        <AnimatedCard
          key={index}
          entranceDelay={index * 100}
          hoverElevation
        >
          {child}
        </AnimatedCard>
      ))}
    </div>
  );
};

// Floating Action Button Animation
interface FloatingActionButtonProps {
  children: ReactNode;
  onClick?: () => void;
  ariaLabel?: string;
}

export const FloatingActionButton: React.FC<FloatingActionButtonProps> = ({
  children,
  onClick,
  ariaLabel,
}) => {
  const scale = useSpringValue(1);
  const rotate = useSpringValue(0);

  const [springs] = useSpring(() => ({
    scale,
    rotate,
    config: { tension: 300, friction: 10 },
  }));

  return (
    <animated.div
      style={{
        ...springs,
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 1000,
      }}
    >
      <IconButton
        onClick={onClick}
        aria-label={ariaLabel}
        onMouseEnter={() => {
          scale.start(1.1);
          rotate.start(10);
        }}
        onMouseLeave={() => {
          scale.start(1);
          rotate.start(0);
        }}
        onMouseDown={() => {
          scale.start(0.95);
        }}
        onMouseUp={() => {
          scale.start(1.1);
        }}
        sx={{
          width: 56,
          height: 56,
          backgroundColor: 'primary.main',
          color: 'white',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
          '&:hover': {
            backgroundColor: 'primary.dark',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.3)',
          },
        }}
      >
        {children}
      </IconButton>
    </animated.div>
  );
};

// Spring-based loading spinner
export const SpringSpinner: React.FC<{ size?: number }> = ({ size = 24 }) => {
  const spinnerSpring = useSpring({
    from: { rotate: 0 },
    to: { rotate: 360 },
    config: { duration: 1000 },
    loop: true,
  });

  return (
    <animated.div
      style={{
        ...spinnerSpring,
        width: size,
        height: size,
        borderRadius: '50%',
        border: `2px solid rgba(20, 184, 138, 0.3)`,
        borderTopColor: '#14b88a',
      }}
    />
  );
};