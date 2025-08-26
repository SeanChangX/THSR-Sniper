#!/usr/bin/env python3
"""
THSR Captcha Model Tester
- Download captcha images from THSR
- Process images using image_processor.py
- Predict using trained OCR model
- Display results for human comparison
"""

import os
import sys
import argparse
import tempfile
import shutil
from pathlib import Path
import time
import subprocess

# ML/AI imports
import numpy as np
import tensorflow as tf
import keras
from keras import ops
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Import local modules
from download_captcha import download_captcha_images
from datasets.image_processor import process_image

# CTC Layer definition (needed for model loading)
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
        # Compute the training-time loss value and add it
        # to the layer using `self.add_loss()`.
        batch_len = ops.cast(ops.shape(y_true)[0], dtype="int64")
        input_length = ops.cast(ops.shape(y_pred)[1], dtype="int64")
        label_length = ops.cast(ops.shape(y_true)[1], dtype="int64")

        input_length = input_length * ops.ones(shape=(batch_len, 1), dtype="int64")
        label_length = label_length * ops.ones(shape=(batch_len, 1), dtype="int64")

        loss = self.loss_fn(y_true, y_pred, input_length, label_length)
        self.add_loss(loss)

        # At test time, just return the computed predictions
        return y_pred
    
    def get_config(self):
        config = super().get_config()
        return config

class CaptchaModelTester:
    def __init__(self, model_path="ocr_model.keras"):
        """
        Initialize the captcha model tester
        
        Args:
            model_path: Path to the trained Keras model
        """
        self.model_path = model_path
        self.model = None
        self.prediction_model = None
        self.char_to_num = None
        self.num_to_char = None
        
        # Model parameters (must match training)
        self.img_width = 160
        self.img_height = 50
        self.max_length = 4  # Assuming 4-character captchas
        
        self.load_model()
    
    def load_model(self):
        """Load the trained model and set up character mappings"""
        print(f"Loading model from: {self.model_path}")
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        # Create custom objects dictionary for model loading
        custom_objects = {
            'CTCLayer': CTCLayer,
            'ctc_batch_cost': ctc_batch_cost,
            'ctc_label_dense_to_sparse': ctc_label_dense_to_sparse
        }
        
        # Try to load model with different strategies
        self.model = None
        self.prediction_model = None
        
        try:
            # Strategy 1: Try loading with custom objects (full model)
            self.model = keras.models.load_model(self.model_path, custom_objects=custom_objects)
            print("Full model loaded successfully")
            
            # Create prediction model (without CTC layer)
            try:
                self.prediction_model = keras.models.Model(
                    self.model.input[0], 
                    self.model.get_layer(name="dense2").output
                )
                print("Prediction model created from full model")
            except Exception as e:
                print(f"Could not extract prediction model: {e}")
                self.prediction_model = self.model
                
        except Exception as e:
            print(f"Could not load as full model: {e}")
            
            # Strategy 2: Try loading as prediction-only model
            try:
                self.prediction_model = keras.models.load_model(self.model_path)
                print("Prediction model loaded directly")
                self.model = self.prediction_model
            except Exception as e2:
                print(f"Could not load model with any strategy: {e2}")
                raise e2
        
        # Set up character mappings (from actual training data)
        # Characters sorted alphabetically as in training script
        characters = ['2', '3', '4', '5', '6', '7', '8', '9', 
                     'C', 'D', 'F', 'G', 'H', 'K', 'M', 'N', 'P', 'R', 'T', 'V', 'W', 'Y', 'Z']
        
        # Try to get vocabulary from model if available, otherwise use default
        try:
            # Try to extract vocabulary from model layers
            for layer in self.model.layers:
                if hasattr(layer, 'vocabulary') and layer.vocabulary is not None:
                    vocab = layer.vocabulary
                    if len(vocab) > 1:  # Skip if empty or just mask token
                        characters = vocab
                        print(f"Using vocabulary from model: {characters}")
                        break
        except:
            print("Could not extract vocabulary from model, using default character set")
        
        # Create character mapping layers
        from keras import layers
        self.char_to_num = layers.StringLookup(vocabulary=list(characters), mask_token=None)
        self.num_to_char = layers.StringLookup(
            vocabulary=self.char_to_num.get_vocabulary(), mask_token=None, invert=True
        )
        
        print(f"Character mappings set up ({len(characters)} characters)")
        print(f"Characters: {characters}")
    
    def preprocess_image(self, image_path):
        """
        Preprocess a single image for model prediction
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image tensor
        """
        # Read and decode image
        img = tf.io.read_file(image_path)
        img = tf.io.decode_jpeg(img, channels=1)  # Grayscale JPEG
        
        # Convert to float32 in [0, 1] range
        img = tf.image.convert_image_dtype(img, tf.float32)
        
        # Resize to model input size
        img = tf.image.resize(img, [self.img_height, self.img_width])
        
        # Transpose for time dimension (width becomes time)
        img = tf.transpose(img, perm=[1, 0, 2])
        
        # Add batch dimension
        img = tf.expand_dims(img, axis=0)
        
        return img
    
    def ctc_decode(self, y_pred, input_length, greedy=True, beam_width=100, top_paths=1):
        """CTC decode function (copied from training script)"""
        input_shape = ops.shape(y_pred)
        num_samples, num_steps = input_shape[0], input_shape[1]
        y_pred = ops.log(ops.transpose(y_pred, axes=[1, 0, 2]) + keras.backend.epsilon())
        input_length = ops.cast(input_length, dtype="int32")

        if greedy:
            (decoded, log_prob) = tf.nn.ctc_greedy_decoder(
                inputs=y_pred, sequence_length=input_length
            )
        else:
            (decoded, log_prob) = tf.compat.v1.nn.ctc_beam_search_decoder(
                inputs=y_pred,
                sequence_length=input_length,
                beam_width=beam_width,
                top_paths=top_paths,
            )
        decoded_dense = []
        for st in decoded:
            st = tf.SparseTensor(st.indices, st.values, (num_samples, num_steps))
            decoded_dense.append(tf.sparse.to_dense(sp_input=st, default_value=-1))
        return (decoded_dense, log_prob)
    
    def decode_batch_predictions(self, pred):
        """Decode model predictions to text"""
        input_len = np.ones(pred.shape[0]) * pred.shape[1]
        # Use greedy search
        results = self.ctc_decode(pred, input_length=input_len, greedy=True)[0][0][
            :, :self.max_length
        ]
        # Convert to text
        output_text = []
        for res in results:
            res = tf.strings.reduce_join(self.num_to_char(res)).numpy().decode("utf-8")
            output_text.append(res)
        return output_text
    
    def predict_image(self, image_path):
        """
        Predict text from a single image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Predicted text string
        """
        # Preprocess image
        img_tensor = self.preprocess_image(image_path)
        
        # Make prediction
        pred = self.prediction_model.predict(img_tensor, verbose=0)
        
        # Decode prediction
        pred_text = self.decode_batch_predictions(pred)[0]
        
        return pred_text
    
    def download_and_test(self, count=5, processing_mode='balanced', show_images=True):
        """
        Download captcha images, process them, and test model predictions
        
        Args:
            count: Number of images to download and test
            processing_mode: Image processing mode ('gentle', 'balanced', 'aggressive')
            show_images: Whether to display images and results
        """
        print(f"\n=== THSR Captcha Model Test ===")
        print(f"Testing {count} images with {processing_mode} processing mode")
        
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            raw_images_dir = temp_path / "raw_images"
            processed_images_dir = temp_path / "processed_images"
            
            print(f"\nStep 1: Downloading {count} captcha images...")
            
            # Download images
            try:
                download_captcha_images(
                    count=count,
                    output_dir=str(raw_images_dir),
                    delay=1.5,
                    also_save_to_tmp=False
                )
            except Exception as e:
                print(f"Error downloading images: {e}")
                return
            
            # Get list of downloaded images
            raw_images = sorted(list(raw_images_dir.glob("captcha_*.jpg")))
            
            if not raw_images:
                print("No images were downloaded successfully")
                return
            
            print(f"Downloaded {len(raw_images)} images")
            
            print(f"\nStep 2: Processing images with {processing_mode} mode...")
            
            # Process images
            processed_images_dir.mkdir(exist_ok=True)
            processed_images = []
            
            for raw_image in raw_images:
                try:
                    # Process using image_processor
                    processed_img = process_image(
                        str(raw_image), 
                        target_size=(self.img_width, self.img_height),
                        mode=processing_mode,
                        preview=False
                    )
                    
                    # Save processed image
                    processed_path = processed_images_dir / raw_image.name
                    processed_img.save(str(processed_path), 'JPEG', quality=95)
                    processed_images.append(processed_path)
                    
                    print(f"Processed: {raw_image.name}")
                    
                except Exception as e:
                    print(f"Error processing {raw_image.name}: {e}")
            
            print(f"Processed {len(processed_images)} images")
            
            print(f"\nStep 3: Running model predictions...")
            
            # Test predictions
            results = []
            for i, processed_image in enumerate(processed_images):
                try:
                    prediction = self.predict_image(str(processed_image))
                    results.append({
                        'filename': processed_image.name,
                        'raw_path': raw_images[i],
                        'processed_path': processed_image,
                        'prediction': prediction
                    })
                    print(f"Predicted {processed_image.name}: {prediction}")
                    
                except Exception as e:
                    print(f"Error predicting {processed_image.name}: {e}")
                    results.append({
                        'filename': processed_image.name,
                        'raw_path': raw_images[i],
                        'processed_path': processed_image,
                        'prediction': f"ERROR: {e}"
                    })
            
            print(f"\nStep 4: Displaying results for human comparison...")
            
            if show_images and results:
                self.display_results(results)
            
            # Print summary
            print(f"\n=== Test Summary ===")
            print(f"Images downloaded: {len(raw_images)}")
            print(f"Images processed: {len(processed_images)}")
            print(f"Predictions made: {len([r for r in results if not r['prediction'].startswith('ERROR')])}")
            
            print(f"\n=== Predictions ===")
            for result in results:
                status = "OK" if not result['prediction'].startswith('ERROR') else "ERR"
                print(f"{status} {result['filename']}: {result['prediction']}")
    
    def display_results(self, results):
        """Display images and predictions for human comparison"""
        if not results:
            return
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            
            # Calculate grid size
            n_results = len(results)
            cols = min(3, n_results)
            rows = (n_results + cols - 1) // cols
            
            fig, axes = plt.subplots(rows * 2, cols, figsize=(4 * cols, 3 * rows * 2))
            
            # Handle different subplot configurations
            if rows == 1 and cols == 1:
                axes = np.array([[axes[0]], [axes[1]]])
            elif rows == 1:
                axes = axes.reshape(2, cols)
            elif cols == 1:
                axes = axes.reshape(rows * 2, 1)
            else:
                axes = axes.reshape(rows * 2, cols)
            
            for i, result in enumerate(results):
                row = i // cols
                col = i % cols
                
                try:
                    # Load and display raw image
                    raw_img = Image.open(result['raw_path'])
                    axes[row * 2, col].imshow(raw_img)
                    axes[row * 2, col].set_title(f"Raw: {result['filename']}")
                    axes[row * 2, col].axis('off')
                    
                    # Load and display processed image
                    processed_img = Image.open(result['processed_path'])
                    axes[row * 2 + 1, col].imshow(processed_img)
                    axes[row * 2 + 1, col].set_title(f"Prediction: {result['prediction']}")
                    axes[row * 2 + 1, col].axis('off')
                    
                except Exception as e:
                    print(f"Error displaying {result['filename']}: {e}")
            
            # Hide unused subplots
            for i in range(n_results, rows * cols):
                row = i // cols
                col = i % cols
                if row * 2 < axes.shape[0] and col < axes.shape[1]:
                    axes[row * 2, col].axis('off')
                if row * 2 + 1 < axes.shape[0] and col < axes.shape[1]:
                    axes[row * 2 + 1, col].axis('off')
            
            plt.tight_layout()
            
            # Save plot instead of showing (for headless environment)
            output_path = "captcha_test_results.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Results saved to: {output_path}")
            plt.close()
            
        except Exception as e:
            print(f"Could not display images: {e}")
            print("Displaying results in text format:")
            for result in results:
                print(f"File: {result['filename']} -> Prediction: {result['prediction']}")
        
        # Ask for user feedback
        print(f"\nCheck the results:")
        print(f"- Images processed and predictions made")
        print(f"- Please manually verify prediction accuracy")
        
        input("\nPress Enter to continue...")

def main():
    parser = argparse.ArgumentParser(description="Test THSR Captcha OCR Model")
    parser.add_argument("--model", "-m", default="ocr_model.keras", 
                       help="Path to trained model (default: ocr_model.keras)")
    parser.add_argument("--count", "-c", type=int, default=5,
                       help="Number of captcha images to test (default: 5)")
    parser.add_argument("--mode", choices=['gentle', 'balanced', 'aggressive'], 
                       default='balanced', help="Image processing mode (default: balanced)")
    parser.add_argument("--no-display", action="store_true",
                       help="Don't display images (just print predictions)")
    
    args = parser.parse_args()
    
    try:
        # Initialize tester
        tester = CaptchaModelTester(args.model)
        
        # Run test
        tester.download_and_test(
            count=args.count,
            processing_mode=args.mode,
            show_images=not args.no_display
        )
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
