#!/usr/bin/env python3
"""
Convert full model to prediction-only model (without CTC layer)
This avoids the CTCLayer loading issues
"""

import os
import sys
import tensorflow as tf
import keras
from keras import ops
from pathlib import Path

# CTC Layer definition (same as training script)
def ctc_batch_cost(y_true, y_pred, input_length, label_length):
    label_length = ops.cast(ops.squeeze(label_length, axis=-1), dtype="int32")
    input_length = ops.cast(ops.squeeze(input_length, axis=-1), dtype="int32")
    sparse_labels = ops.cast(
        ctc_label_dense_to_sparse(y_true, label_length), dtype="int32"
    )

    y_pred = ops.log(ops.transpose(y_pred, axes=[1, 0, 2]) + keras.backend.epsilon())

    return ops.expand_dims(
        tf.compat.v1.nn.ctc_loss(
            inputs=y_pred, labels=sparse_labels, sequence_length=input_length
        ),
        1,
    )

def ctc_label_dense_to_sparse(labels, label_lengths):
    label_shape = ops.shape(labels)
    num_batches_tns = ops.stack([label_shape[0]])
    max_num_labels_tns = ops.stack([label_shape[1]])

    def range_less_than(old_input, current_input):
        return ops.expand_dims(ops.arange(ops.shape(old_input)[1]), 0) < tf.fill(
            max_num_labels_tns, current_input
        )

    init = ops.cast(tf.fill([1, label_shape[1]], 0), dtype="bool")
    dense_mask = tf.compat.v1.scan(
        range_less_than, label_lengths, initializer=init, parallel_iterations=1
    )
    dense_mask = dense_mask[:, 0, :]

    label_array = ops.reshape(
        ops.tile(ops.arange(0, label_shape[1]), num_batches_tns), label_shape
    )
    label_ind = tf.compat.v1.boolean_mask(label_array, dense_mask)

    batch_array = ops.transpose(
        ops.reshape(
            ops.tile(ops.arange(0, label_shape[0]), max_num_labels_tns),
            tf.reverse(label_shape, [0]),
        )
    )
    batch_ind = tf.compat.v1.boolean_mask(batch_array, dense_mask)
    indices = ops.transpose(
        ops.reshape(ops.concatenate([batch_ind, label_ind], axis=0), [2, -1])
    )

    vals_sparse = tf.compat.v1.gather_nd(labels, indices)

    return tf.SparseTensor(
        ops.cast(indices, dtype="int64"),
        vals_sparse,
        ops.cast(label_shape, dtype="int64")
    )

@keras.saving.register_keras_serializable()
class CTCLayer(keras.layers.Layer):
    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.loss_fn = ctc_batch_cost

    def call(self, y_true, y_pred):
        batch_len = ops.cast(ops.shape(y_true)[0], dtype="int64")
        input_length = ops.cast(ops.shape(y_pred)[1], dtype="int64")
        label_length = ops.cast(ops.shape(y_true)[1], dtype="int64")

        input_length = input_length * ops.ones(shape=(batch_len, 1), dtype="int64")
        label_length = label_length * ops.ones(shape=(batch_len, 1), dtype="int64")

        loss = self.loss_fn(y_true, y_pred, input_length, label_length)
        self.add_loss(loss)

        return y_pred
    
    def get_config(self):
        config = super().get_config()
        return config

def convert_model(input_model_path, output_model_path):
    """Convert full model to prediction-only model"""
    print(f"Loading full model from: {input_model_path}")
    
    # Create custom objects dictionary
    custom_objects = {
        'CTCLayer': CTCLayer,
        'ctc_batch_cost': ctc_batch_cost,
        'ctc_label_dense_to_sparse': ctc_label_dense_to_sparse
    }
    
    try:
        # Load the full model
        full_model = keras.models.load_model(input_model_path, custom_objects=custom_objects)
        print("Full model loaded successfully!")
        
        # Create prediction model (without CTC layer)
        prediction_model = keras.models.Model(
            full_model.input[0], 
            full_model.get_layer(name="dense2").output
        )
        
        print("Prediction model created!")
        print(f"Input shape: {prediction_model.input_shape}")
        print(f"Output shape: {prediction_model.output_shape}")
        
        # Save prediction model
        prediction_model.save(output_model_path)
        print(f"Prediction model saved to: {output_model_path}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    input_model = "thsr_ocr_model_250827.keras"
    output_model = "thsr_prediction_model.keras"
    
    if not os.path.exists(input_model):
        print(f"Input model not found: {input_model}")
        exit(1)
    
    success = convert_model(input_model, output_model)
    
    if success:
        print(f"\nModel conversion completed!")
        print(f"You can now use: python test_model.py -m {output_model}")
    else:
        print(f"\nModel conversion failed!")
