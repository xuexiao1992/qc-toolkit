import unittest

from qctoolkit.pulses.repetition_pulse_template import RepetitionPulseTemplate,ParameterNotIntegerException
from qctoolkit.pulses.parameters import ParameterDeclaration, ParameterNotProvidedException, ParameterValueIllegalException
from qctoolkit.pulses.instructions import REPJInstruction, InstructionPointer

from tests.pulses.sequencing_dummies import DummyPulseTemplate, DummySequencer, DummyInstructionBlock, DummyParameter, DummyCondition
from tests.serialization_dummies import DummySerializer


class RepetitionPulseTemplateTest(unittest.TestCase):

    def test_init(self) -> None:
        body = DummyPulseTemplate()
        repetition_count = 3
        t = RepetitionPulseTemplate(body, repetition_count)
        self.assertEqual(repetition_count, t.repetition_count)
        self.assertEqual(body, t.body)

        repetition_count = ParameterDeclaration('foo')
        t = RepetitionPulseTemplate(body, repetition_count)
        self.assertEqual(repetition_count, t.repetition_count)
        self.assertEqual(body, t.body)

    def test_parameter_names_and_declarations(self) -> None:
        body = DummyPulseTemplate()
        t = RepetitionPulseTemplate(body, 5)
        self.assertEqual(body.parameter_names, t.parameter_names)
        self.assertEqual(body.parameter_declarations, t.parameter_declarations)

        body.parameter_names_ = {'foo', 't', 'bar'}
        self.assertEqual(body.parameter_names, t.parameter_names)
        self.assertEqual(body.parameter_declarations, t.parameter_declarations)

    def test_is_interruptable(self) -> None:
        body = DummyPulseTemplate(is_interruptable=False)
        t = RepetitionPulseTemplate(body, 6)
        self.assertFalse(t.is_interruptable)

        body.is_interruptable_ = True
        self.assertTrue(t.is_interruptable)

    def test_str(self) -> None:
        body = DummyPulseTemplate()
        t = RepetitionPulseTemplate(body, 9)
        self.assertIsInstance(str(t), str)
        t = RepetitionPulseTemplate(body, ParameterDeclaration('foo'))
        self.assertIsInstance(str(t), str)


class RepetitionPulseTemplateSequencingTests(unittest.TestCase):

    def test_requires_stop_constant(self) -> None:
        body = DummyPulseTemplate(requires_stop=False)
        t = RepetitionPulseTemplate(body, 2)
        self.assertFalse(t.requires_stop({}, {}))
        body.requires_stop_ = True
        self.assertFalse(t.requires_stop({}, {}))

    def test_requires_stop_declaration(self) -> None:
        body = DummyPulseTemplate(requires_stop=False)
        t = RepetitionPulseTemplate(body, ParameterDeclaration('foo'))

        parameter = DummyParameter()
        parameters = dict(foo=parameter)
        condition = DummyCondition()
        conditions = dict(foo=condition)

        for body_requires_stop in [True, False]:
            for condition_requires_stop in [True, False]:
                for parameter_requires_stop in [True, False]:
                    body.requires_stop_ = body_requires_stop
                    condition.requires_stop_ = condition_requires_stop
                    parameter.requires_stop_ = parameter_requires_stop
                    self.assertEqual(parameter_requires_stop, t.requires_stop(parameters, conditions))

    def setUp(self) -> None:
        self.body = DummyPulseTemplate()
        self.repetitions = ParameterDeclaration('foo', max=5)
        self.template = RepetitionPulseTemplate(self.body, self.repetitions)
        self.sequencer = DummySequencer()
        self.block = DummyInstructionBlock()

    def test_build_sequence_constant(self) -> None:
        repetitions = 3
        t = RepetitionPulseTemplate(self.body, repetitions)
        parameters = {}
        conditions = dict(foo=DummyCondition(requires_stop=True))
        t.build_sequence(self.sequencer, parameters, conditions, self.block)

        self.assertTrue(self.block.embedded_blocks)
        body_block = self.block.embedded_blocks[0]
        self.assertEqual({body_block}, set(self.sequencer.sequencing_stacks.keys()))
        self.assertEqual([(self.body, parameters, conditions)], self.sequencer.sequencing_stacks[body_block])
        self.assertEqual([REPJInstruction(repetitions, InstructionPointer(body_block, 0))], self.block.instructions)

    def test_build_sequence_declaration_success(self) -> None:
        parameters = dict(foo=3)
        conditions = dict(foo=DummyCondition(requires_stop=True))
        self.template.build_sequence(self.sequencer, parameters, conditions, self.block)

        self.assertTrue(self.block.embedded_blocks)
        body_block = self.block.embedded_blocks[0]
        self.assertEqual({body_block}, set(self.sequencer.sequencing_stacks.keys()))
        self.assertEqual([(self.body, parameters, conditions)],
                         self.sequencer.sequencing_stacks[body_block])
        self.assertEqual([REPJInstruction(parameters['foo'], InstructionPointer(body_block, 0))], self.block.instructions)


    def test_build_sequence_declaration_exceeds_bounds(self) -> None:
        parameters = dict(foo=9)
        conditions = dict(foo=DummyCondition(requires_stop=True))
        with self.assertRaises(ParameterValueIllegalException):
            self.template.build_sequence(self.sequencer, parameters, conditions, self.block)
        self.assertFalse(self.sequencer.sequencing_stacks)

    def test_build_sequence_declaration_parameter_missing(self) -> None:
        parameters = {}
        conditions = dict(foo=DummyCondition(requires_stop=True))
        with self.assertRaises(ParameterNotProvidedException):
            self.template.build_sequence(self.sequencer, parameters, conditions, self.block)
        self.assertFalse(self.sequencer.sequencing_stacks)

    def test_build_sequence_declaration_parameter_value_not_whole(self) -> None:
        parameters = dict(foo=3.3)
        conditions = dict(foo=DummyCondition(requires_stop=True))
        with self.assertRaises(ParameterNotIntegerException):
            self.template.build_sequence(self.sequencer, parameters, conditions, self.block)
        self.assertFalse(self.sequencer.sequencing_stacks)


class RepetitionPulseTemplateSerializationTests(unittest.TestCase):

    def setUp(self) -> None:
        self.serializer = DummySerializer(deserialize_callback=lambda x: x['name'])
        self.body = DummyPulseTemplate()

    def test_get_serialization_data_constant(self) -> None:
        repetition_count = 3
        template = RepetitionPulseTemplate(self.body, repetition_count)
        expected_data = dict(
            type=self.serializer.get_type_identifier(template),
            body=str(id(self.body)),
            repetition_count=repetition_count
        )
        data = template.get_serialization_data(self.serializer)
        self.assertEqual(expected_data, data)

    def test_get_serialization_data_declaration(self) -> None:
        repetition_count = ParameterDeclaration('foo')
        template = RepetitionPulseTemplate(self.body, repetition_count)
        expected_data = dict(
            type=self.serializer.get_type_identifier(template),
            body=str(id(self.body)),
            repetition_count=str(id(repetition_count))
        )
        data = template.get_serialization_data(self.serializer)
        self.assertEqual(expected_data, data)

    def test_deserialize_constant(self) -> None:
        repetition_count = 3
        data = dict(
            repetition_count=repetition_count,
            body=dict(name=str(id(self.body))),
            identifier='foo'
        )
        # prepare dependencies for deserialization
        self.serializer.subelements[str(id(self.body))] = self.body
        # deserialize
        template = RepetitionPulseTemplate.deserialize(self.serializer, **data)
        # compare!
        self.assertEqual(self.body, template.body)
        self.assertEqual(repetition_count, template.repetition_count)

    def test_deserialize_declaration(self) -> None:
        repetition_count = ParameterDeclaration('foo')
        data = dict(
            repetition_count=dict(name='foo'),
            body=dict(name=str(id(self.body))),
            identifier='foo'
        )
        # prepare dependencies for deserialization
        self.serializer.subelements[str(id(self.body))] = self.body
        self.serializer.subelements['foo'] = repetition_count
        # deserialize
        template = RepetitionPulseTemplate.deserialize(self.serializer, **data)
        # compare!
        self.assertEqual(self.body, template.body)
        self.assertEqual(repetition_count, template.repetition_count)


class ParameterNotIntegerExceptionTests(unittest.TestCase):

    def test(self) -> None:
        exception = ParameterNotIntegerException('foo', 3)
        self.assertIsInstance(str(exception), str)


if __name__ == "__main__":
    unittest.main(verbosity=2)