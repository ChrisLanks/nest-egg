/**
 * Drawer shown in edit mode for adding widgets not currently in the layout.
 */

import {
  Button,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  HStack,
  Text,
  VStack,
  Badge,
} from '@chakra-ui/react';
import { WIDGET_REGISTRY } from './widgetRegistry';
import type { LayoutItem } from './types';

interface AddWidgetDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentLayout: LayoutItem[];
  onAdd: (widgetId: string) => void;
}

export const AddWidgetDrawer: React.FC<AddWidgetDrawerProps> = ({
  isOpen,
  onClose,
  currentLayout,
  onAdd,
}) => {
  const activeIds = new Set(currentLayout.map((item) => item.id));
  const availableWidgets = Object.values(WIDGET_REGISTRY).filter(
    (def) => !activeIds.has(def.id)
  );

  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="sm">
      <DrawerOverlay />
      <DrawerContent>
        <DrawerCloseButton />
        <DrawerHeader borderBottomWidth="1px">Add Widget</DrawerHeader>
        <DrawerBody pt={4}>
          {availableWidgets.length === 0 ? (
            <Text color="gray.500" textAlign="center" mt={8}>
              All widgets are already on your dashboard.
            </Text>
          ) : (
            <VStack align="stretch" spacing={3}>
              {availableWidgets.map((def) => (
                <HStack
                  key={def.id}
                  p={4}
                  borderWidth={1}
                  borderRadius="md"
                  justify="space-between"
                  align="start"
                  _hover={{ bg: 'gray.50' }}
                >
                  <VStack align="start" spacing={1} flex={1} mr={3}>
                    <HStack spacing={2}>
                      <Text fontWeight="semibold" fontSize="sm">
                        {def.title}
                      </Text>
                      <Badge
                        colorScheme="gray"
                        fontSize="xs"
                        variant="subtle"
                      >
                        {def.defaultSpan === 2 ? 'full width' : 'half width'}
                      </Badge>
                    </HStack>
                    <Text fontSize="xs" color="gray.600">
                      {def.description}
                    </Text>
                  </VStack>
                  <Button
                    size="sm"
                    colorScheme="brand"
                    flexShrink={0}
                    onClick={() => {
                      onAdd(def.id);
                      onClose();
                    }}
                  >
                    Add
                  </Button>
                </HStack>
              ))}
            </VStack>
          )}
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
};
