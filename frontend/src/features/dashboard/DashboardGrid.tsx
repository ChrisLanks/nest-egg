/**
 * Dashboard grid with drag-and-drop reordering in edit mode.
 *
 * Layout is a flat ordered list rendered into a 2-column CSS grid.
 * Items with span=2 fill the full row; span=1 items share a row.
 * Drag-and-drop (dnd-kit) reorders the flat list; the grid reflowss naturally.
 */

import {
  Box,
  Button,
  HStack,
  Icon,
  IconButton,
  Text,
  Tooltip,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { MdDragIndicator, MdViewColumn, MdViewStream } from 'react-icons/md';
import { CloseIcon, AddIcon } from '@chakra-ui/icons';
import type { LayoutItem } from './types';
import { WIDGET_REGISTRY } from './widgetRegistry';

// ── SortableWidget ──────────────────────────────────────────────────────────

interface SortableWidgetProps {
  item: LayoutItem;
  isEditing: boolean;
  onRemove: (id: string) => void;
  onSpanToggle: (id: string) => void;
}

const SortableWidget: React.FC<SortableWidgetProps> = ({
  item,
  isEditing,
  onRemove,
  onSpanToggle,
}) => {
  const def = WIDGET_REGISTRY[item.id];
  const editBarBg = useColorModeValue('whiteAlpha.900', 'blackAlpha.800');
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.id,
    disabled: !isEditing,
  });

  const style: React.CSSProperties = {
    gridColumn: item.span === 2 ? 'span 2' : 'span 1',
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    position: 'relative',
  };

  if (!def) return null;

  const WidgetComponent = def.component;

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      {isEditing && (
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          zIndex={10}
          bg={editBarBg}
          borderTopRadius="md"
          px={3}
          py={2}
          borderBottom="1px solid"
          borderColor="border.default"
        >
          <HStack justify="space-between">
            <HStack spacing={2}>
              <Box
                {...listeners}
                cursor="grab"
                display="flex"
                alignItems="center"
                color="text.muted"
                _hover={{ color: 'text.secondary' }}
              >
                <Icon as={MdDragIndicator} boxSize={5} />
              </Box>
              <Text fontSize="sm" fontWeight="medium" color="text.heading">
                {def.title}
              </Text>
            </HStack>
            <HStack spacing={1}>
              <Tooltip label={item.span === 2 ? 'Switch to half width' : 'Switch to full width'}>
                <IconButton
                  aria-label="Toggle width"
                  icon={<Icon as={item.span === 2 ? MdViewColumn : MdViewStream} />}
                  size="xs"
                  variant="ghost"
                  onClick={() => onSpanToggle(item.id)}
                />
              </Tooltip>
              <Tooltip label="Remove widget">
                <IconButton
                  aria-label="Remove widget"
                  icon={<CloseIcon boxSize={2.5} />}
                  size="xs"
                  variant="ghost"
                  colorScheme="red"
                  onClick={() => onRemove(item.id)}
                />
              </Tooltip>
            </HStack>
          </HStack>
        </Box>
      )}
      <Box pt={isEditing ? '48px' : 0}>
        <WidgetComponent />
      </Box>
    </div>
  );
};

// ── DashboardGrid ───────────────────────────────────────────────────────────

interface DashboardGridProps {
  layout: LayoutItem[];
  isEditing: boolean;
  onLayoutChange: (layout: LayoutItem[]) => void;
  onAddWidget: () => void;
}

export const DashboardGrid: React.FC<DashboardGridProps> = ({
  layout,
  isEditing,
  onLayoutChange,
  onAddWidget,
}) => {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = layout.findIndex((item) => item.id === active.id);
      const newIndex = layout.findIndex((item) => item.id === over.id);
      onLayoutChange(arrayMove(layout, oldIndex, newIndex));
    }
  };

  const handleRemove = (id: string) => {
    onLayoutChange(layout.filter((item) => item.id !== id));
  };

  const handleSpanToggle = (id: string) => {
    onLayoutChange(
      layout.map((item) =>
        item.id === id ? { ...item, span: item.span === 2 ? 1 : 2 } : item
      )
    );
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={layout.map((item) => item.id)} strategy={verticalListSortingStrategy}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '24px',
          }}
        >
          {layout.map((item) => (
            <SortableWidget
              key={item.id}
              item={item}
              isEditing={isEditing}
              onRemove={handleRemove}
              onSpanToggle={handleSpanToggle}
            />
          ))}
        </div>
      </SortableContext>

      {isEditing && (
        <Box mt={6} display="flex" justifyContent="center">
          <Button
            leftIcon={<AddIcon />}
            variant="outline"
            colorScheme="brand"
            onClick={onAddWidget}
          >
            Add Widget
          </Button>
        </Box>
      )}
    </DndContext>
  );
};
