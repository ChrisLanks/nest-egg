/**
 * Standardized empty state component for pages with no data
 */

import { Box, VStack, Heading, Text, Button, Icon } from '@chakra-ui/react';
import { ReactElement } from 'react';

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
      bg="gray.50"
      borderRadius="lg"
      borderWidth={1}
      borderColor="gray.200"
    >
      <VStack spacing={4}>
        {icon && (
          <Box
            borderRadius="full"
            bg="gray.100"
            p={6}
            display="inline-flex"
            alignItems="center"
            justifyContent="center"
          >
            <Icon as={icon} boxSize={`${config.iconSize}px`} color="gray.400" />
          </Box>
        )}

        <VStack spacing={2}>
          <Heading size={config.titleSize} color="gray.700">
            {title}
          </Heading>

          {description && (
            <Text color="gray.600" maxW="md">
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
