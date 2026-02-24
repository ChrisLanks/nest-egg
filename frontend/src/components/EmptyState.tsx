/**
 * Standardized empty state component for pages with no data
 */

import { Box, VStack, Heading, Text, Button, Icon } from '@chakra-ui/react';
import React from 'react';

interface EmptyStateProps {
  /** Icon to display (from react-icons) */
  icon?: React.ElementType;
  /** Main title */
  title: string;
  /** Description text */
  description?: string;
  /** Action button text */
  actionLabel?: string;
  /** Action button click handler */
  onAction?: () => void;
  /** Show action button only if condition is true */
  showAction?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

export const EmptyState = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  showAction = true,
  size = 'md',
}: EmptyStateProps) => {
  const sizeConfig = {
    sm: {
      iconSize: 40,
      titleSize: 'md',
      py: 8,
    },
    md: {
      iconSize: 64,
      titleSize: 'lg',
      py: 12,
    },
    lg: {
      iconSize: 80,
      titleSize: 'xl',
      py: 16,
    },
  };

  const config = sizeConfig[size];

  return (
    <Box
      py={config.py}
      px={6}
      textAlign="center"
      bg="bg.subtle"
      borderRadius="lg"
      borderWidth={1}
      borderColor="border.default"
    >
      <VStack spacing={4}>
        {icon && (
          <Box
            borderRadius="full"
            bg="bg.muted"
            p={6}
            display="inline-flex"
            alignItems="center"
            justifyContent="center"
          >
            <Icon as={icon} boxSize={`${config.iconSize}px`} color="text.muted" />
          </Box>
        )}

        <VStack spacing={2}>
          <Heading size={config.titleSize} color="text.heading">
            {title}
          </Heading>

          {description && (
            <Text color="text.secondary" maxW="md">
              {description}
            </Text>
          )}
        </VStack>

        {showAction && actionLabel && onAction && (
          <Button colorScheme="brand" onClick={onAction} mt={2}>
            {actionLabel}
          </Button>
        )}
      </VStack>
    </Box>
  );
};
