/**
 * ScrollableTable — wraps a table with horizontal scroll and a visual
 * fade hint on the right edge when content overflows on mobile.
 */
import { Box, useBreakpointValue } from "@chakra-ui/react";
import { ReactNode, useCallback, useEffect, useRef, useState } from "react";

interface ScrollableTableProps {
  children: ReactNode;
}

export const ScrollableTable = ({ children }: ScrollableTableProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showHint, setShowHint] = useState(false);
  const isMobile = useBreakpointValue({ base: true, md: false });

  const checkOverflow = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    // Show hint if there's more content to the right
    setShowHint(el.scrollWidth > el.clientWidth + el.scrollLeft + 2);
  }, []);

  useEffect(() => {
    checkOverflow();
    window.addEventListener("resize", checkOverflow);
    return () => window.removeEventListener("resize", checkOverflow);
  }, [checkOverflow]);

  return (
    <Box position="relative">
      <Box
        ref={scrollRef}
        overflowX="auto"
        onScroll={checkOverflow}
        role="region"
        aria-label="Scrollable table"
      >
        {children}
      </Box>
      {isMobile && showHint && (
        <Box
          position="absolute"
          right={0}
          top={0}
          bottom={0}
          width="24px"
          pointerEvents="none"
          bgGradient="linear(to-r, transparent, var(--chakra-colors-chakra-body-bg))"
          opacity={0.8}
        />
      )}
    </Box>
  );
};
