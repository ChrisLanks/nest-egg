/**
 * Reusable infinite scroll sentinel component
 * Automatically triggers loadMore when scrolled into view
 */

import { useEffect, useRef } from 'react';
import { Box, Center, VStack, Spinner, Text } from '@chakra-ui/react';

interface InfiniteScrollSentinelProps {
  hasMore: boolean;
  isLoading: boolean;
  onLoadMore: () => void;
  loadingText?: string;
  endText?: string;
  showEndIndicator?: boolean;
}

export const InfiniteScrollSentinel = ({
  hasMore,
  isLoading,
  onLoadMore,
  loadingText = 'Loading more...',
  endText = 'No more items to load',
  showEndIndicator = true,
}: InfiniteScrollSentinelProps) => {
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Intersection observer for infinite scroll
  useEffect(() => {
    if (!sentinelRef.current || !hasMore || isLoading) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          onLoadMore();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(sentinelRef.current);

    return () => {
      observer.disconnect();
    };
  }, [hasMore, isLoading, onLoadMore]);

  if (hasMore) {
    return (
      <Box ref={sentinelRef} py={8}>
        <Center>
          {isLoading && (
            <VStack spacing={2}>
              <Spinner size="lg" color="brand.500" />
              <Text fontSize="sm" color="text.secondary">
                {loadingText}
              </Text>
            </VStack>
          )}
        </Center>
      </Box>
    );
  }

  if (showEndIndicator) {
    return (
      <Box py={4}>
        <Center>
          <Text fontSize="sm" color="text.muted">
            {endText}
          </Text>
        </Center>
      </Box>
    );
  }

  return null;
};
